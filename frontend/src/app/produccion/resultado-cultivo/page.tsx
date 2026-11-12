"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ConsolidadoCampaniaView } from "@/components/resultado-cultivo/ConsolidadoCampaniaView";
import { SelectorCultivoCampania } from "@/components/resultado-cultivo/FormularioAccess";
import { FormularioResultados } from "@/components/resultado-cultivo/FormularioResultados";
import { SelectorCampania } from "@/components/resultado-cultivo/SelectorCampania";
import { PageHeader } from "@/components/ui/PageHeader";
import { fetchCampanias, fetchResultadoCampania } from "@/services/resultadoCultivoApi";

/** Resultado de cultivo: formato y cálculos del formulario FrmResultados de Access; "Toda la campaña" conserva el consolidado. */
export default function ResultadoCultivoPage() {
  const [vista, setVista] = useState<"cultivo" | "campania">("cultivo");
  const [idCultivo, setIdCultivo] = useState<number | null>(null);
  const [idCampania, setIdCampania] = useState<number | null>(null);
  const [campaniaConsolidado, setCampaniaConsolidado] = useState<number | null>(null);
  const campanias = useQuery({ queryKey: ["resultado-cultivo", "campanias"], queryFn: fetchCampanias, enabled: vista === "campania" });
  const idCons = campaniaConsolidado ?? campanias.data?.campaniaActualId ?? null;
  const consolidado = useQuery({
    queryKey: ["resultado-cultivo", "campania", idCons], queryFn: () => fetchResultadoCampania(idCons!),
    enabled: vista === "campania" && idCons !== null,
  });

  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Resultado de cultivo" ayuda="Igual que el formulario Resultados de Access: superficies, rindes, costos directos, ventas, deducciones, margen bruto y rentabilidad, en pesos y dólares.">
        <div role="tablist" className="flex rounded-md border border-border p-0.5 text-sm">
          {(["cultivo", "campania"] as const).map((v) => (
            <button key={v} type="button" role="tab" aria-selected={vista === v} onClick={() => setVista(v)}
              className={`rounded px-3 py-1 ${vista === v ? "bg-agro text-white" : "text-ink-secondary hover:text-ink-primary"}`}>
              {v === "cultivo" ? "Por cultivo" : "Toda la campaña"}
            </button>
          ))}
        </div>
      </PageHeader>

      {vista === "cultivo" ? (
        <div className="space-y-3">
          <SelectorCultivoCampania idCultivo={idCultivo} idCampania={idCampania} onCultivo={setIdCultivo} onCampania={setIdCampania} />
          {idCultivo !== null && idCampania !== null
            ? <FormularioResultados idCultivo={idCultivo} idCampania={idCampania} />
            : <p className="text-sm text-ink-secondary">Elegí cultivo y campaña.</p>}
        </div>
      ) : (
        <div className="space-y-3">
          <SelectorCampania campanias={campanias.data?.campanias ?? []} seleccionada={idCons} cargando={campanias.isPending} onChange={setCampaniaConsolidado} />
          <ConsolidadoCampaniaView datos={consolidado.data} cargando={campanias.isPending || consolidado.isPending}
            error={campanias.isError || consolidado.isError}
            onReintentar={() => (campanias.isError ? campanias.refetch() : consolidado.refetch())} idCultivoSeleccionado={null} />
        </div>
      )}
    </main>
  );
}
