"use client";

import { useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/States";

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

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  keyField: (row: T) => React.Key;
  emptyMessage: string;
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

type SortState = { key: string; direction: "asc" | "desc" } | null;

/**
 * Tabla de datos densa con ordenamiento por columna y paginación
 * (design/agroux-frontend-redesign.md §4.1). El ordenamiento opera sobre
 * la página cargada (no re-consulta el servidor) — suficiente para el
 * volumen actual de estos módulos; si un módulo crece a miles de filas
 * por página, mover el sort al backend.
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
}: DataTableProps<T>) {
  const [sort, setSort] = useState<SortState>(null);
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const sortedRows = useMemo(() => {
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
  }, [rows, sort, columns]);

  function toggleSort(column: DataTableColumn<T>) {
    if (!column.sortValue) return;
    setSort((prev) => {
      if (prev?.key !== column.key) return { key: column.key, direction: "asc" };
      if (prev.direction === "asc") return { key: column.key, direction: "desc" };
      return null;
    });
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
                    className={`px-3 py-1.5 font-medium text-ink-secondary ${
                      col.align === "right" ? "text-right" : "text-left"
                    } ${col.sortValue ? "cursor-pointer select-none hover:text-ink-primary" : ""}`}
                    onClick={() => toggleSort(col)}
                  >
                    {col.header}
                    {active && <span className="ml-1">{sort!.direction === "asc" ? "▲" : "▼"}</span>}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {sortedRows.map((row) => (
              <tr key={keyField(row)} className="hover:bg-surface-sunken">
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
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm text-ink-secondary">
        <span>
          Página {page} de {totalPages} — {total} resultados
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
