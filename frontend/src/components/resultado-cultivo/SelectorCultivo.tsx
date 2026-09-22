"use client";

import type { ResultadoCultivoResumen } from "@/services/resultadoCultivoApi";

export function SelectorCultivo({
  cultivos,
  onChange,
}: {
  cultivos: ResultadoCultivoResumen[];
  onChange: (id: number | null) => void;
}) {
  return (
    <label className="block min-w-56 text-sm font-medium text-ink-primary">
      Ir directo a un cultivo
      <select
        className="mt-1 block w-full rounded border border-border bg-surface px-3 py-2"
        value=""
        disabled={cultivos.length === 0}
        onChange={(event) => onChange(event.target.value ? Number(event.target.value) : null)}
      >
        <option value="">Elegir cultivo…</option>
        {cultivos.map((item) => (
          <option key={item.idCultivo} value={item.idCultivo}>
            {item.cultivo}
          </option>
        ))}
      </select>
    </label>
  );
}
