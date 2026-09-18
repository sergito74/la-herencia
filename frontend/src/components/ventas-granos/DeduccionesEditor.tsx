"use client";

import type { DeduccionInput } from "@/services/ventasGranosApi";
import type { FiltrosVentaGranosResponse } from "@/services/ventasGranosApi";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { filterInputClass } from "@/components/ui/FilterBar";

function filaVacia(filtros: FiltrosVentaGranosResponse | undefined): DeduccionInput {
  return {
    idConcepto: filtros?.conceptosDeducciones[0]?.idConcepto ?? 0,
    detalle: "",
    porc: 0,
    baseCalculo: 0,
    alicuota: 0,
  };
}

/**
 * Lista editable simple de Deducciones de una Venta de Granos (restan del
 * total, data-model.md) — mismo criterio que `AjustesEditor`: sin grilla
 * tipo planilla (research.md §3, tasks.md T069).
 */
export function DeduccionesEditor({
  deducciones,
  onChange,
  filtros,
}: {
  deducciones: DeduccionInput[];
  onChange: (deducciones: DeduccionInput[]) => void;
  filtros: FiltrosVentaGranosResponse | undefined;
}) {
  function actualizar(index: number, patch: Partial<DeduccionInput>) {
    const next = [...deducciones];
    next[index] = { ...next[index], ...patch };
    onChange(next);
  }

  function agregar() {
    onChange([...deducciones, filaVacia(filtros)]);
  }

  function quitar(index: number) {
    onChange(deducciones.filter((_, i) => i !== index));
  }

  return (
    <div className="rounded-md border border-border bg-surface p-2">
      <h3 className="text-xs font-medium text-ink-secondary">Deducciones (restan del total)</h3>
      <div className="mt-1 space-y-1">
        {deducciones.map((d, i) => (
          <div key={i} className="flex flex-wrap items-center gap-1">
            <select
              className={`${filterInputClass} min-w-[10rem] px-1.5 py-0.5 text-xs`}
              value={d.idConcepto}
              onChange={(e) => actualizar(i, { idConcepto: Number(e.target.value) })}
            >
              {filtros?.conceptosDeducciones.map((c) => (
                <option key={c.idConcepto} value={c.idConcepto}>
                  {c.concepto ?? `#${c.idConcepto}`}
                </option>
              ))}
            </select>
            <input
              className={`${filterInputClass} min-w-[8rem] flex-1 px-1.5 py-0.5 text-xs`}
              value={d.detalle ?? ""}
              onChange={(e) => actualizar(i, { detalle: e.target.value })}
              placeholder="Detalle"
            />
            <input
              type="number"
              className={`${filterInputClass} w-16 px-1.5 py-0.5 text-right text-xs font-data`}
              value={d.porc}
              onChange={(e) => actualizar(i, { porc: Number(e.target.value) || 0 })}
              title="Porcentaje sobre la base de cálculo"
            />
            <MoneyInput
              className={`${filterInputClass} w-28 px-1.5 py-0.5 text-right text-xs font-data`}
              value={d.baseCalculo}
              moneda="Pesos"
              onChange={(baseCalculo) => actualizar(i, { baseCalculo })}
            />
            <input
              type="number"
              className={`${filterInputClass} w-16 px-1.5 py-0.5 text-right text-xs font-data`}
              value={d.alicuota ?? 0}
              onChange={(e) => actualizar(i, { alicuota: Number(e.target.value) || 0 })}
              title="Alícuota de IVA de esta deducción"
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
        disabled={!filtros?.conceptosDeducciones.length}
        className="mt-1 rounded-sm border border-border px-2 py-1 text-xs text-ink-secondary hover:border-border-strong hover:text-ink-primary disabled:opacity-40"
      >
        + Agregar deducción
      </button>
    </div>
  );
}
