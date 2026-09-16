"use client";

import { useState } from "react";

import { RetencionesVentaHaciendaListado } from "@/components/ventas-hacienda/RetencionesVentaHaciendaListado";
import { VentasHaciendaListado } from "@/components/ventas-hacienda/VentasHaciendaListado";

const TABS = ["Ventas", "Retenciones"] as const;

export default function VentasHaciendaPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Ventas");

  return (
    <main className="mx-auto max-w-6xl p-8">
      <h1 className="text-2xl font-semibold">Ventas de hacienda</h1>
      <p className="mt-1 text-ink-secondary">
        Ventas de hacienda y retenciones asociadas (solo lectura).
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
        {tab === "Ventas" ? <VentasHaciendaListado /> : <RetencionesVentaHaciendaListado />}
      </div>
    </main>
  );
}
