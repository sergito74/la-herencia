"use client";

import type { CampaniaItem } from "@/services/resultadoCultivoApi";

export function SelectorCampania({
  campanias,
  seleccionada,
  cargando,
  onChange,
}: {
  campanias: CampaniaItem[];
  seleccionada: number | null;
  cargando: boolean;
  onChange: (id: number) => void;
}) {
  return (
    <label className="block min-w-56 text-sm font-medium text-ink-primary">
      Campaña
      <select
        className="mt-1 block w-full rounded border border-border bg-surface px-3 py-2"
        value={seleccionada ?? ""}
        disabled={cargando || campanias.length === 0}
        onChange={(event) => onChange(Number(event.target.value))}
      >
        {cargando && <option value="">Cargando campañas…</option>}
        {!cargando && campanias.length === 0 && <option value="">No hay campañas</option>}
        {campanias.map((item) => (
          <option key={item.idCampania} value={item.idCampania}>
            {item.campania}
          </option>
        ))}
      </select>
    </label>
  );
}
