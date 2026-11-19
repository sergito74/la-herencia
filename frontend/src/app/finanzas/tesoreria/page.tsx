"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { MEDIO_LABELS, MovimientosPorMedio } from "@/components/tesoreria/MovimientosPorMedio";
import { CargaExtracto } from "@/components/tesoreria/CargaExtracto";
import { ListadosEstudio } from "@/components/tesoreria/ListadosEstudio";
import { Segmentos } from "@/components/ui/Segmentos";
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
      <PageHeader titulo="Tesorería" ayuda="Consulta y conciliación de movimientos por banco, caja, valores y tarjetas.">
        <div className="ml-auto"><CargaExtracto /></div>
      </PageHeader>
      <ListadosEstudio />

      <Segmentos etiqueta="Medio" valor={medio} onChange={setMedio} opciones={MEDIOS.map((m) => ({ id: m, label: MEDIO_LABELS[m] }))} />

      <div className="mt-3">
        <MovimientosPorMedio medio={medio} highlightKey={highlight ? Number(highlight) : undefined} />
      </div>

    </main>
  );
}
