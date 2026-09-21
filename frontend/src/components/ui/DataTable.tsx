"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { EmptyState } from "@/components/ui/States";
import { formatCantidad } from "@/lib/format";

export interface DataTableColumn<T> {
  key: string;
  header: string;
  align?: "left" | "right";
  /** Aplica `.font-data` (tabular-nums) — usar en toda columna numérica/fecha/moneda. */
  numeric?: boolean;
  render: (row: T) => React.ReactNode;
  /** Si se define, la columna admite ordenamiento por click en el header. */
  sortValue?: (row: T) => string | number | null;
}

export type SortState = { key: string; direction: "asc" | "desc" } | null;

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  keyField: (row: T) => React.Key;
  emptyMessage: string;
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  /**
   * Resalta y hace scroll hacia la fila cuya `keyField()` coincida — usado
   * para los links bidireccionales desde Cuenta Corriente hacia su
   * módulo de origen (design/erp-module-architecture.md §3.3/§3.4).
   */
  highlightKey?: React.Key | null;
  /**
   * Ordenamiento controlado por el padre (ej. el backend ordena y
   * pagina) — si se pasan `sort`+`onSortChange`, se usan estos en vez del
   * estado interno, y las filas recibidas NO se reordenan localmente (se
   * asume que ya vienen ordenadas). Sin estos props, se mantiene el
   * comportamiento anterior: ordena solo las filas de la página cargada,
   * sin volver a consultar el servidor.
   */
  sort?: SortState;
  onSortChange?: (sort: SortState) => void;
}

/**
 * Tabla de datos densa con ordenamiento por columna y paginación
 * (design/agroux-frontend-redesign.md §4.1).
 */
export function DataTable<T>({
  columns,
  rows,
  keyField,
  emptyMessage,
  page,
  pageSize,
  total,
  onPageChange,
  highlightKey,
  sort: controlledSort,
  onSortChange,
}: DataTableProps<T>) {
  const [internalSort, setInternalSort] = useState<SortState>(null);
  const controlado = onSortChange != null;
  const sort = controlado ? controlledSort ?? null : internalSort;
  const highlightRef = useRef<HTMLTableRowElement | null>(null);
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  useEffect(() => {
    if (highlightKey != null && highlightRef.current) {
      highlightRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlightKey]);

  const sortedRows = useMemo(() => {
    if (controlado) return rows; // ya viene ordenado por el servidor
    if (!sort) return rows;
    const column = columns.find((c) => c.key === sort.key);
    if (!column?.sortValue) return rows;
    const factor = sort.direction === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const va = column.sortValue!(a);
      const vb = column.sortValue!(b);
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (va < vb) return -1 * factor;
      if (va > vb) return 1 * factor;
      return 0;
    });
  }, [rows, sort, columns, controlado]);

  function toggleSort(column: DataTableColumn<T>) {
    if (!column.sortValue) return;
    const next: SortState =
      sort?.key !== column.key
        ? { key: column.key, direction: "asc" }
        : sort.direction === "asc"
          ? { key: column.key, direction: "desc" }
          : null;
    if (controlado) onSortChange!(next);
    else setInternalSort(next);
  }

  if (rows.length === 0) {
    return <EmptyState message={emptyMessage} />;
  }

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto rounded-md border border-border bg-surface">
        <table className="min-w-full divide-y divide-border text-sm">
          <thead className="bg-surface-sunken text-left">
            <tr>
              {columns.map((col) => {
                const active = sort?.key === col.key;
                return (
                  <th
                    key={col.key}
                    title={col.sortValue ? "Ordenar por esta columna" : undefined}
                    className={`px-3 py-1.5 font-medium text-ink-secondary ${
                      col.align === "right" ? "text-right" : "text-left"
                    } ${col.sortValue ? "cursor-pointer select-none hover:text-ink-primary" : ""}`}
                    onClick={() => toggleSort(col)}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.header}
                      {col.sortValue && (
                        <span className={`text-[0.6rem] leading-none ${active ? "text-finance" : "text-ink-muted"}`}>
                          {active ? (sort!.direction === "asc" ? "▲" : "▼") : "⇅"}
                        </span>
                      )}
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {sortedRows.map((row) => {
              const key = keyField(row);
              const isHighlighted = highlightKey != null && String(key) === String(highlightKey);
              return (
                <tr
                  key={key}
                  ref={isHighlighted ? highlightRef : undefined}
                  className={isHighlighted ? "bg-status-warning-bg" : "hover:bg-surface-sunken"}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={`px-3 py-1.5 ${col.align === "right" ? "text-right" : ""} ${
                        col.numeric ? "font-data" : ""
                      }`}
                    >
                      {col.render(row)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm text-ink-secondary">
        <span>
          Página {page} de {totalPages} — {formatCantidad(total)} resultados
        </span>
        <div className="flex gap-2">
          <button
            className="rounded-sm border border-border px-3 py-1 disabled:opacity-40"
            disabled={page <= 1}
            onClick={() => onPageChange(Math.max(1, page - 1))}
          >
            Anterior
          </button>
          <button
            className="rounded-sm border border-border px-3 py-1 disabled:opacity-40"
            disabled={page >= totalPages}
            onClick={() => onPageChange(page + 1)}
          >
            Siguiente
          </button>
        </div>
      </div>
    </div>
  );
}
