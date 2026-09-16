"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { ImpuestosListado } from "@/components/impuestos/ImpuestosListado";
import { RetencionesListado } from "@/components/impuestos/RetencionesListado";

const TABS = ["Impuestos", "Retenciones"] as const;

export default function ImpuestosPage() {
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const [tab, setTab] = useState<(typeof TABS)[number]>(
    tabParam === "retenciones" ? "Retenciones" : "Impuestos"
  );
  const highlight = searchParams.get("highlight");
  const highlightKey = highlight ? Number(highlight) : undefined;

  return (
    <main className="mx-auto max-w-6xl p-8">
      <h1 className="text-2xl font-semibold">Impuestos</h1>
      <p className="mt-1 text-ink-secondary">
        Impuestos y retenciones impositivas (solo lectura).
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
        {tab === "Impuestos" ? (
          <ImpuestosListado highlightKey={tab === "Impuestos" ? highlightKey : undefined} />
        ) : (
          <RetencionesListado highlightKey={tab === "Retenciones" ? highlightKey : undefined} />
        )}
      </div>
    </main>
  );
}
