"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { useState } from "react";

import { ComparacionCultivoCampania } from "@/components/imputacion/ComparacionCultivoCampania";
import { apiGet } from "@/services/apiClient";
import type { ComparacionCampaniaOut } from "@/services/imputacionApi";

export default function ComparacionPage() {
  const [idCampania, setIdCampania] = useState<number | null>(null);
  const [comparacion, setComparacion] = useState<ComparacionCampaniaOut | null>(null);
  const [cargando, setCargando] = useState(false);

  async function buscar() {
    if (!idCampania) return;
    setCargando(true);
    try {
      const resultado = await apiGet<ComparacionCampaniaOut>("/api/imputacion/comparacion", { idCampania });
      setComparacion(resultado);
    } finally {
      setCargando(false);
    }
  }

  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Comparación motor heredado vs. motor nuevo" volver="/imputacion" ayuda="El motor heredado sigue siendo la fuente oficial de Resultado y Costos de Cultivo mientras se valida el motor nuevo." />

      <div className="flex items-end gap-2">
        <label className="text-sm">
          Campaña (IdCampania)
          <input
            type="number"
            value={idCampania ?? ""}
            onChange={(e) => setIdCampania(e.target.value ? Number(e.target.value) : null)}
            className="mt-1 block w-32 rounded-sm border border-border px-2 py-1.5 text-right"
          />
        </label>
        <button
          type="button"
          onClick={buscar}
          disabled={!idCampania || cargando}
          className="rounded-md bg-agro px-3 py-1.5 text-sm text-white disabled:opacity-60"
        >
          {cargando ? "Comparando…" : "Comparar"}
        </button>
      </div>

      {comparacion && (
        <div className="mt-3">
          <ComparacionCultivoCampania comparacion={comparacion} />
        </div>
      )}
    </main>
  );
}
