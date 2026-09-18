"use client";

import type { LineaConsumoInput } from "@/services/tarjetasResumenesApi";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { filterInputClass } from "@/components/ui/FilterBar";

const FILA_VACIA: LineaConsumoInput = {
  fechaCompra: "",
  detalle: "",
  importe: 0,
  fechaVencimientoCompra: null,
  idContacto: null,
  nroDocumento: null,
};

/**
 * Grilla editable de líneas de consumo de un resumen (Historia 1). La
 * mayoría de las líneas reales no tienen contacto ni documento cargado
 * (edge case documentado en spec.md) — ambos campos son opcionales.
 */
export function LineasConsumoEditor({
  lineas,
  onChange,
}: {
  lineas: LineaConsumoInput[];
  onChange: (lineas: LineaConsumoInput[]) => void;
}) {
  function actualizar(index: number, patch: Partial<LineaConsumoInput>) {
    const next = [...lineas];
    next[index] = { ...next[index], ...patch };
    onChange(next);
  }

  function agregar() {
    onChange([...lineas, { ...FILA_VACIA }]);
  }

  function quitar(index: number) {
    onChange(lineas.filter((_, i) => i !== index));
  }

  return (
    <div className="rounded-md border border-border bg-surface p-2">
      <h3 className="text-xs font-medium text-ink-secondary">
        Líneas de consumo {lineas.length === 0 && "(ninguna — resumen solo cabecera)"}
      </h3>
      <div className="mt-1 space-y-1">
        {lineas.map((l, i) => (
          <div key={i} className="flex flex-wrap items-center gap-1">
            <input
              type="date"
              required
              className={`${filterInputClass} px-1.5 py-0.5 text-xs`}
              value={l.fechaCompra}
              onChange={(e) => actualizar(i, { fechaCompra: e.target.value })}
            />
            <input
              className={`${filterInputClass} min-w-[10rem] flex-1 px-1.5 py-0.5 text-xs`}
              value={l.detalle}
              onChange={(e) => actualizar(i, { detalle: e.target.value.slice(0, 255) })}
              placeholder="Detalle"
              required
            />
            <MoneyInput
              className={`${filterInputClass} w-28 px-1.5 py-0.5 text-right text-xs font-data`}
              value={l.importe}
              moneda="Pesos"
              onChange={(importe) => actualizar(i, { importe })}
            />
            <input
              type="date"
              className={`${filterInputClass} px-1.5 py-0.5 text-xs`}
              value={l.fechaVencimientoCompra ?? ""}
              onChange={(e) => actualizar(i, { fechaVencimientoCompra: e.target.value || null })}
              title="Fecha de vencimiento (opcional)"
            />
            <div className="w-40">
              <ContactoSelect
                value={l.idContacto ?? null}
                razonSocial={null}
                onChange={(id) => actualizar(i, { idContacto: id })}
                placeholder="Contacto (opcional)"
              />
            </div>
            <input
              className={`${filterInputClass} w-28 px-1.5 py-0.5 text-xs`}
              value={l.nroDocumento ?? ""}
              onChange={(e) => actualizar(i, { nroDocumento: e.target.value || null })}
              placeholder="Nº doc. (opcional)"
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
        + Agregar línea
      </button>
    </div>
  );
}
