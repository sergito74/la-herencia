"use client";

import type { VencimientoVentaInput } from "@/services/ventasHaciendaApi";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { filterInputClass } from "@/components/ui/FilterBar";

/**
 * Fechas de vencimiento de una Venta de Hacienda (007) — a diferencia de
 * Compras, acá cada vencimiento tiene su propio importe (data-model.md,
 * FR-004), así que este editor no puede reusar `VencimientosEditor.tsx` de
 * Compras tal cual (su `VencimientoInput` no tiene `importe`); se duplica
 * adaptado en vez de forzar un tipo compartido entre ambos dominios.
 */
export function VencimientosVentaHaciendaEditor({
  vencimientos,
  onChange,
}: {
  vencimientos: VencimientoVentaInput[];
  onChange: (vencimientos: VencimientoVentaInput[]) => void;
}) {
  function actualizar(index: number, patch: Partial<VencimientoVentaInput>) {
    const next = [...vencimientos];
    next[index] = { ...next[index], ...patch };
    onChange(next);
  }

  function agregar() {
    onChange([...vencimientos, { fecha: "", importe: 0 }]);
  }

  function quitar(index: number) {
    onChange(vencimientos.filter((_, i) => i !== index));
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {vencimientos.map((v, i) => (
        <div key={i} className="flex items-center gap-1">
          <input
            type="date"
            required
            className={filterInputClass}
            value={v.fecha}
            onChange={(e) => actualizar(i, { fecha: e.target.value })}
          />
          <MoneyInput
            className={`${filterInputClass} w-28 text-right font-data`}
            value={v.importe}
            moneda="Pesos"
            onChange={(importe) => actualizar(i, { importe })}
          />
          <button
            type="button"
            onClick={() => quitar(i)}
            className="rounded-sm border border-border px-1.5 py-0.5 text-xs text-ink-secondary hover:text-status-danger"
          >
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={agregar}
        className="rounded-sm border border-border px-2 py-1 text-xs text-ink-secondary hover:border-border-strong hover:text-ink-primary"
      >
        + Agregar vencimiento
      </button>
    </div>
  );
}
