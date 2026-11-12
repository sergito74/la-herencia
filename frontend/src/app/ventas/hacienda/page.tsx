"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import Link from "next/link";

import { VentasHaciendaListado } from "@/components/ventas-hacienda/VentasHaciendaListado";
import { Suspense } from "react";
import { NuevosParaRevisar } from "@/components/documentos-nuevos/NuevosParaRevisar";
import { SoloLectura } from "@/components/auth/SoloLectura";

export default function VentasHaciendaPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <Suspense fallback={null}>
        <NuevosParaRevisar modulo="ventas" />
      </Suspense>
      <PageHeader titulo="Ventas de hacienda">
        <SoloLectura>
          <Link
            href="/ventas/hacienda/nueva"
            className="rounded-sm bg-agro px-3 py-1 text-sm text-white hover:opacity-90"
          >
            + Nueva venta de hacienda
          </Link>
        </SoloLectura>
      </PageHeader>
      <div>
        <VentasHaciendaListado />
      </div>
    </main>
  );
}
