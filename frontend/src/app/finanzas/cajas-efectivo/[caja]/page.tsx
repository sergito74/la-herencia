import { notFound } from "next/navigation";

import { CajaEfectivo } from "@/components/cajas-efectivo/CajaEfectivo";
import type { CajaSlug } from "@/services/cajasEfectivoApi";
import { BackLink } from "@/components/ui/BackLink";
import { CajasNav } from "@/components/cajas-efectivo/CajasNav";
import { Suspense } from "react";

const CAJAS_VALIDAS: CajaSlug[] = ["giamigli-sa", "campo-chica", "condominio-lsc", "giamigli-dolares"];

export const metadata = {
  title: "Caja de efectivo",
};

export default function CajaEfectivoPage({ params }: { params: { caja: string } }) {
  const { caja } = params;
  if (!CAJAS_VALIDAS.includes(caja as CajaSlug)) {
    notFound();
  }

  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/finanzas/cajas">Volver a Cajas y socios</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Caja de efectivo</h1>
      <p className="mt-1 text-ink-secondary">
        Movimientos, pagos, aportes, traspasos, arqueos y comparación con la planilla.
      </p>
      <div className="mt-4"><CajasNav /></div>
      <div className="mt-6">
        <Suspense><CajaEfectivo caja={caja as CajaSlug} /></Suspense>
      </div>
    </main>
  );
}
