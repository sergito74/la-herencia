"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { MEDIO_LABELS, MovimientosPorMedio } from "@/components/tesoreria/MovimientosPorMedio";
import { CargaExcel } from "@/components/tesoreria/CargaExcel";
import { CargaExtractoPdf } from "@/components/tesoreria/CargaExtractoPdf";
import { NuevosParaRevisar } from "@/components/documentos-nuevos/NuevosParaRevisar";
import type { Medio } from "@/services/tesoreriaApi";

const MEDIOS: Medio[] = [
  "bna",
  "galicia",
  "mercado-libre",
  "efectivo",
  "valores-propios",
  "valores-recibidos",
  "tarjetas",
];

function isMedio(value: string | null): value is Medio {
  return MEDIOS.includes(value as Medio);
}

export default function TesoreriaPage() {
  const searchParams = useSearchParams();
  const medioParam = searchParams.get("medio");
  const [medio, setMedio] = useState<Medio>(isMedio(medioParam) ? medioParam : "bna");
  const highlight = searchParams.get("highlight");

  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <Suspense fallback={null}>
        <NuevosParaRevisar modulo="tesoreria" />
      </Suspense>
      <PageHeader titulo="Tesorería" ayuda="Consulta y conciliación de movimientos por banco, caja, valores y tarjetas." />

      <div className="flex flex-wrap gap-2">
        {MEDIOS.map((m) => (
          <button
            key={m}
            className={`rounded px-3 py-1.5 text-sm ${
              m === medio
                ? "bg-finance text-white"
                : "border border-border text-ink-primary hover:bg-surface-sunken"
            }`}
            onClick={() => setMedio(m)}
          >
            {MEDIO_LABELS[m]}
          </button>
        ))}
      </div>

      <div className="mt-3">
        <MovimientosPorMedio medio={medio} highlightKey={highlight ? Number(highlight) : undefined} />
      </div>

      <div className="mt-8">
        <CargaExtractoPdf />
      </div>

      <div className="mt-4">
        <CargaExcel />
      </div>
    </main>
  );
}
