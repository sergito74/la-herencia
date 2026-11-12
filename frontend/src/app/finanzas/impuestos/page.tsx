"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { ImpuestosListado } from "@/components/impuestos/ImpuestosListado";
import { RetencionesListado } from "@/components/impuestos/RetencionesListado";
import { RetencionesVentaHaciendaListado } from "@/components/ventas-hacienda/RetencionesVentaHaciendaListado";
import { NuevosParaRevisar } from "@/components/documentos-nuevos/NuevosParaRevisar";

const TABS = ["Impuestos", "Retenciones", "Retenciones Venta Hacienda"] as const;

export default function ImpuestosPage() {
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const [tab, setTab] = useState<(typeof TABS)[number]>(
    tabParam === "retenciones-venta-hacienda"
      ? "Retenciones Venta Hacienda"
      : tabParam === "retenciones"
        ? "Retenciones"
        : "Impuestos"
  );
  const highlight = searchParams.get("highlight");
  const highlightKey = highlight ? Number(highlight) : undefined;

  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <Suspense fallback={null}>
        <NuevosParaRevisar modulo="impuestos" />
      </Suspense>
      <PageHeader titulo="Impuestos" ayuda="Boletas de impuestos (alta, edición y baja) y retenciones impositivas (solo lectura)." />

      <div className="flex gap-2">
        {TABS.map((t) => (
          <button
            key={t}
            className={`rounded px-3 py-1.5 text-sm ${
              t === tab
                ? "bg-finance text-white"
                : "border border-border text-ink-primary hover:bg-surface-sunken"
            }`}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="mt-3">
        {tab === "Impuestos" && <ImpuestosListado highlightKey={highlightKey} />}
        {tab === "Retenciones" && <RetencionesListado highlightKey={highlightKey} />}
        {tab === "Retenciones Venta Hacienda" && (
          <RetencionesVentaHaciendaListado highlightKey={highlightKey} />
        )}
      </div>
    </main>
  );
}
