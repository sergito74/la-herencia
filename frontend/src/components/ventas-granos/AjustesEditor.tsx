"use client";

import type { AjusteInput } from "@/services/ventasGranosApi";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { filterInputClass } from "@/components/ui/FilterBar";

const FILA_VACIA: AjusteInput = { concepto: "", importe: 0, alicuotaIVA: 0 };

/**
 * Lista editable simple de Ajustes de una Venta de Granos (suman al
 * subtotal, data-model.md) — a propósito NO es una grilla tipo planilla
 * como `ComprasGrid`/`VentaHaciendaGrid`: son ajustes puntuales, no líneas
 * de producto (research.md §3, tasks.md T069).
 */
export function AjustesEditor({
  ajustes,
  onChange,
}: {
  ajustes: AjusteInput[];
  onChange: (ajustes: AjusteInput[]) => void;
}) {
  function actualizar(index: number, patch: Partial<AjusteInput>) {
    const next = [...ajustes];
    next[index] = { ...next[index], ...patch };
    onChange(next);
  }

  function agregar() {
    onChange([...ajustes, { ...FILA_VACIA }]);
  }

  function quitar(index: number) {
    onChange(ajustes.filter((_, i) => i !== index));
  }

  return (
    <div className="rounded-md border border-border bg-surface p-2">
      <h3 className="text-xs font-medium text-ink-secondary">Ajustes (suman al subtotal)</h3>
      <div className="mt-1 space-y-1">
        {ajustes.map((a, i) => (
          <div key={i} className="flex flex-wrap items-center gap-1">
            <input
              className={`${filterInputClass} min-w-[10rem] flex-1 px-1.5 py-0.5 text-xs`}
              value={a.concepto}
              onChange={(e) => actualizar(i, { concepto: e.target.value })}
              placeholder="Concepto"
            />
            <MoneyInput
              className={`${filterInputClass} w-28 px-1.5 py-0.5 text-right text-xs font-data`}
              value={a.importe}
              moneda="Pesos"
              onChange={(importe) => actualizar(i, { importe })}
            />
            <input
              type="number"
              className={`${filterInputClass} w-20 px-1.5 py-0.5 text-right text-xs font-data`}
              value={a.alicuotaIVA ?? 0}
              onChange={(e) => actualizar(i, { alicuotaIVA: Number(e.target.value) || 0 })}
              title="Alícuota IVA (informativo)"
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
      </div>
      <button
        type="button"
        onClick={agregar}
        className="mt-1 rounded-sm border border-border px-2 py-1 text-xs text-ink-secondary hover:border-border-strong hover:text-ink-primary"
      >
        + Agregar ajuste
      </button>
    </div>
  );
}
