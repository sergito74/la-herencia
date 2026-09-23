import Link from "next/link";
import { Suspense } from "react";

import { VentasGranosListado } from "@/components/ventas-granos/VentasGranosListado";
import { LoadingState } from "@/components/ui/States";
import { BackLink } from "@/components/ui/BackLink";
import { SoloLectura } from "@/components/auth/SoloLectura";

export const metadata = {
  title: "Ventas de granos",
};

export default function VentasGranosPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <div className="mt-2 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Ventas de granos</h1>
          <p className="mt-1 text-ink-secondary">Ventas de granos liquidadas, con ajustes y deducciones.</p>
        </div>
        <SoloLectura>
          <Link
            href="/ventas/granos/nueva"
            className="rounded-sm bg-agro px-4 py-2 text-sm text-white hover:opacity-90"
          >
            + Nueva venta de granos
          </Link>
        </SoloLectura>
      </div>
      <div className="mt-6">
        <Suspense fallback={<LoadingState />}>
          <VentasGranosListado />
        </Suspense>
      </div>
    </main>
  );
}
