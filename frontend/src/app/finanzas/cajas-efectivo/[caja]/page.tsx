import { PageHeader } from "@/components/ui/PageHeader";
import { notFound } from "next/navigation";

import { CajaEfectivo } from "@/components/cajas-efectivo/CajaEfectivo";
import type { CajaSlug } from "@/services/cajasEfectivoApi";
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
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo={caja === "condominio-lsc" ? "Condominio LSC — Movimientos vinculados" : "Caja de efectivo"} volver="/finanzas/cajas"
        ayuda={caja === "condominio-lsc" ? "Relaciones documentadas con Giamigli; la administración del Condominio sigue en su propio sistema." : "Movimientos, pagos, aportes, traspasos, arqueos y comparación con la planilla."} />
      <CajasNav />
      <div className="mt-3">
        <Suspense><CajaEfectivo key={caja} caja={caja as CajaSlug} /></Suspense>
      </div>
    </main>
  );
}
