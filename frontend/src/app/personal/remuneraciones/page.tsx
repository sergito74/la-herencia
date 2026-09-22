"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { PagosRemuneracionListado } from "@/components/remuneraciones/PagosRemuneracionListado";
import { RemuneracionesListado } from "@/components/remuneraciones/RemuneracionesListado";
import { BackLink } from "@/components/ui/BackLink";

const TABS = ["Liquidaciones", "Pagos"] as const;

export default function RemuneracionesPage() {
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<(typeof TABS)[number]>("Liquidaciones");
  const highlight = searchParams.get("highlight");
  const highlightKey = highlight ? Number(highlight) : undefined;

  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Remuneraciones</h1>
      <p className="mt-1 text-ink-secondary">
        Liquidaciones de remuneraciones y pagos efectivos (solo lectura).
      </p>

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

      <div className="mt-6">
        {tab === "Liquidaciones" ? (
          <RemuneracionesListado highlightKey={highlightKey} />
        ) : (
          <PagosRemuneracionListado />
        )}
      </div>
    </main>
  );
}
