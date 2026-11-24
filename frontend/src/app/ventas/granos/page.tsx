import { PageHeader } from "@/components/ui/PageHeader";
import Link from "next/link";
import { Suspense } from "react";

import { VentasGranosListado } from "@/components/ventas-granos/VentasGranosListado";
import { LoadingState } from "@/components/ui/States";
import { NuevosParaRevisar } from "@/components/documentos-nuevos/NuevosParaRevisar";
import { SoloLectura } from "@/components/auth/SoloLectura";

export const metadata = {
  title: "Ventas de granos",
};

export default function VentasGranosPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <Suspense fallback={null}>
        <NuevosParaRevisar modulo="granos" />
      </Suspense>
      <PageHeader titulo="Ventas de granos">
        <SoloLectura>
          <Link
            href="/ventas/granos/nueva"
            className="rounded-md bg-finance font-medium text-white shadow-sm transition-colors hover:bg-finance/90 disabled:opacity-60 px-3 py-1 text-sm hover:opacity-90"
          >
            + Nueva venta de granos
          </Link>
        </SoloLectura>
      </PageHeader>
      <div>
        <Suspense fallback={<LoadingState />}>
          <VentasGranosListado />
        </Suspense>
      </div>
    </main>
  );
}
