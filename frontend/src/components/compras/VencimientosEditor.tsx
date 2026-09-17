"use client";

import type { VencimientoInput } from "@/services/comprasApi";
import { filterInputClass } from "@/components/ui/FilterBar";

/**
 * Fechas de vencimiento de pago (006-carga-compras, FR-008), visible solo
 * cuando la condición de pago es "A Plazo" (ver `CompraForm`, que controla
 * el selector Contado/A Plazo). El esquema real (`Vencimiento Compras`)
 * solo tiene fecha, sin monto por cuota — confirmado por inspección Access.
 */
export function VencimientosEditor({
  vencimientos,
  onChange,
}: {
  vencimientos: VencimientoInput[];
  onChange: (vencimientos: VencimientoInput[]) => void;
}) {
  function actualizarFecha(index: number, fecha: string) {
    const next = [...vencimientos];
    next[index] = { fechaVencimiento: fecha };
    onChange(next);
  }

  function agregar() {
    onChange([...vencimientos, { fechaVencimiento: "" }]);
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
            value={v.fechaVencimiento}
            onChange={(e) => actualizarFecha(i, e.target.value)}
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
        + Agregar fecha
      </button>
    </div>
  );
}
