"use client";

import { useState } from "react";

import { ImpuestosListado } from "@/components/impuestos/ImpuestosListado";
import { RetencionesListado } from "@/components/impuestos/RetencionesListado";

const TABS = ["Impuestos", "Retenciones"] as const;

export default function ImpuestosPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Impuestos");

  return (
    <main className="mx-auto max-w-6xl p-8">
      <h1 className="text-2xl font-semibold">Impuestos</h1>
      <p className="mt-1 text-slate-600">
        Impuestos y retenciones impositivas (solo lectura).
      </p>

      <div className="mt-6 flex gap-2">
        {TABS.map((t) => (
          <button
            key={t}
            className={`rounded px-3 py-1.5 text-sm ${
              t === tab
                ? "bg-slate-900 text-white"
                : "border border-slate-300 text-slate-700 hover:bg-slate-100"
            }`}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === "Impuestos" ? <ImpuestosListado /> : <RetencionesListado />}
      </div>
    </main>
  );
}
