"use client";

import { useId, useState } from "react";

import type { FiltrosVentaHaciendaResponse, LineaVentaHaciendaInput } from "@/services/ventasHaciendaApi";
import { formatMonto, parseNumeroLocal } from "@/lib/format";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { CeldaNumerica } from "@/components/ui/CeldaNumerica";

/**
 * Grilla de líneas de Venta de Hacienda (007): a diferencia de Compras, el
 * comprador es POR LÍNEA (no hay un único proveedor de cabecera) — cada fila
 * incorpora su propio `ContactoSelect`, todas comparten la misma queryKey de
 * búsqueda de contactos (`ContactoSelect` ya cachea por `[query, tipos]`, así
 * que no hace falta nada especial acá para compartir cache entre instancias).
 */
export interface GridRowHacienda {
  idComprador: number | null;
  compradorNombre: string | null;
  idTipoProducto: string;
  cantidad: string;
  unidadMedida: string;
  pesoTotal: string;
  precioUnitarioA: string;
  precioUnitarioB: string;
}

export const FILA_VACIA_HACIENDA: GridRowHacienda = {
  idComprador: null,
  compradorNombre: null,
  idTipoProducto: "",
  cantidad: "",
  unidadMedida: "",
  pesoTotal: "",
  precioUnitarioA: "",
  precioUnitarioB: "",
};

function esFilaVacia(row: GridRowHacienda): boolean {
  return (
    row.idComprador == null &&
    !row.idTipoProducto &&
    !row.cantidad.trim() &&
    !row.pesoTotal.trim() &&
    !row.precioUnitarioA.trim() &&
    !row.precioUnitarioB.trim()
  );
}

export function calcularImporteLineaHacienda(row: GridRowHacienda): number {
  const cantidad = parseNumeroLocal(row.cantidad);
  const precioA = parseNumeroLocal(row.precioUnitarioA);
  const precioB = parseNumeroLocal(row.precioUnitarioB);
  return cantidad * (precioA + precioB);
}

/** Convierte las filas no vacías de la grilla al contrato de línea de la API. */
export function filasARequestLineasHacienda(rows: GridRowHacienda[]): LineaVentaHaciendaInput[] {
  return rows
    .filter((r) => !esFilaVacia(r))
    .map((r) => ({
      idComprador: r.idComprador as number,
      idTipoProducto: Number(r.idTipoProducto),
      cantidad: parseNumeroLocal(r.cantidad),
      unidadMedida: r.unidadMedida || null,
      pesoTotal: r.pesoTotal ? parseNumeroLocal(r.pesoTotal) : null,
      precioUnitarioA: parseNumeroLocal(r.precioUnitarioA),
      precioUnitarioB: r.precioUnitarioB ? parseNumeroLocal(r.precioUnitarioB) : 0,
    }));
}

const inputClass =
  "w-full border-0 bg-transparent px-1.5 py-0.5 text-xs text-ink-primary focus:bg-finance-light focus:outline-none";

export function VentaHaciendaGrid({
  rows,
  onChange,
  filtros,
}: {
  rows: GridRowHacienda[];
  onChange: (rows: GridRowHacienda[]) => void;
  filtros: FiltrosVentaHaciendaResponse | undefined;
}) {
  const listIdBase = useId();
  const unidadesListId = `${listIdBase}-unidades`;

  function actualizarFila(rowIndex: number, patch: Partial<GridRowHacienda>) {
    const next = rows.map((r, i) => (i === rowIndex ? { ...r, ...patch } : r));
    if (!next.some(esFilaVacia)) {
      for (let i = 0; i < 5; i++) next.push({ ...FILA_VACIA_HACIENDA });
    }
    onChange(next);
  }

  function quitarFila(rowIndex: number) {
    onChange(rows.filter((_, i) => i !== rowIndex));
  }

  const totalImporte = rows.reduce((acc, r) => acc + calcularImporteLineaHacienda(r), 0);

  return (
    <div className="space-y-1">
      <datalist id={unidadesListId} />
      <div className="overflow-x-auto rounded-md border border-border">
        <table className="min-w-full divide-y divide-border text-xs">
          <thead className="sticky top-0 bg-surface-sunken text-left">
            <tr>
              {[
                "Comprador",
                "Categoría",
                "Cantidad",
                "Unidad",
                "Peso total",
                "Precio unit. (A)",
                "Precio unit. (B)",
                "Importe",
                "",
              ].map((h) => (
                <th key={h} className="whitespace-nowrap px-1.5 py-1 font-medium text-ink-secondary">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((row, rowIndex) => {
              const importe = calcularImporteLineaHacienda(row);
              return (
                <tr key={rowIndex} className="hover:bg-surface-sunken">
                  <td className="min-w-[14rem]">
                    <ContactoSelect
                      tipoContacto={["Comprador", "Multiple"]}
                      value={row.idComprador}
                      razonSocial={row.compradorNombre}
                      onChange={(id, nombre) =>
                        actualizarFila(rowIndex, { idComprador: id, compradorNombre: nombre })
                      }
                      placeholder="Buscar comprador…"
                    />
                  </td>
                  <td className="min-w-[10rem]">
                    <select
                      className={inputClass}
                      value={row.idTipoProducto}
                      onChange={(e) => actualizarFila(rowIndex, { idTipoProducto: e.target.value })}
                    >
                      <option value="">—</option>
                      {filtros?.tiposHacienda.map((t) => (
                        <option key={t.idTipoHacienda} value={t.idTipoHacienda}>
                          {t.tipoHacienda ?? `#${t.idTipoHacienda}`}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="w-24">
                    <CeldaNumerica
                      className={`${inputClass} font-data text-right`}
                      value={row.cantidad}
                      onChange={(v) => actualizarFila(rowIndex, { cantidad: v })}
                    />
                  </td>
                  <td className="w-24">
                    <input
                      className={inputClass}
                      list={unidadesListId}
                      value={row.unidadMedida}
                      onChange={(e) => actualizarFila(rowIndex, { unidadMedida: e.target.value })}
                    />
                  </td>
                  <td className="w-24">
                    <CeldaNumerica
                      className={`${inputClass} font-data text-right`}
                      value={row.pesoTotal}
                      onChange={(v) => actualizarFila(rowIndex, { pesoTotal: v })}
                    />
                  </td>
                  <td className="w-28">
                    <CeldaNumerica
                      className={`${inputClass} font-data text-right`}
                      value={row.precioUnitarioA}
                      onChange={(v) => actualizarFila(rowIndex, { precioUnitarioA: v })}
                      minDecimales={2}
                      maxDecimales={4}
                    />
                  </td>
                  <td className="w-28">
                    <CeldaNumerica
                      className={`${inputClass} font-data text-right`}
                      value={row.precioUnitarioB}
                      onChange={(v) => actualizarFila(rowIndex, { precioUnitarioB: v })}
                      minDecimales={2}
                      maxDecimales={4}
                    />
                  </td>
                  <td className="w-24 px-1.5 py-0.5 text-right font-data text-ink-secondary">
                    {importe ? formatMonto(importe) : ""}
                  </td>
                  <td className="w-8">
                    {!esFilaVacia(row) && (
                      <button
                        type="button"
                        onClick={() => quitarFila(rowIndex)}
                        className="rounded-sm border border-border px-1.5 py-0.5 text-ink-secondary hover:text-status-danger"
                      >
                        ✕
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot className="sticky bottom-0 bg-surface-sunken font-medium">
            <tr>
              <td colSpan={7} className="px-1.5 py-1 text-right text-ink-secondary">
                Total líneas:
              </td>
              <td className="px-1.5 py-1 text-right font-data">{formatMonto(totalImporte)}</td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
