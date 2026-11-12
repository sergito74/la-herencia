"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { PagosRemuneracionListado } from "@/components/remuneraciones/PagosRemuneracionListado";
import { RemuneracionesListado } from "@/components/remuneraciones/RemuneracionesListado";

const TABS = ["Liquidaciones", "Pagos"] as const;

export default function RemuneracionesPage() {
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<(typeof TABS)[number]>("Liquidaciones");
  const highlight = searchParams.get("highlight");
  const highlightKey = highlight ? Number(highlight) : undefined;
  const empleadoInicial = searchParams.get("empleado");

  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Remuneraciones" />

      <div className="mt-6 flex gap-2">
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
        {tab === "Liquidaciones" ? (
          <RemuneracionesListado highlightKey={highlightKey} empleadoInicial={empleadoInicial} />
        ) : (
          <PagosRemuneracionListado />
        )}
      </div>
    </main>
  );
}
