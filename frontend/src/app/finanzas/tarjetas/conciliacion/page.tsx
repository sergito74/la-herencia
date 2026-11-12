"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { BandejaConciliacion } from "@/components/tarjetas-conciliacion/BandejaConciliacion";
import { TarjetasSubNav } from "@/components/tarjetas/TarjetasSubNav";

export default function ConciliacionPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Conciliación de consumos" volver="/finanzas/tarjetas" />
      <div>
        <TarjetasSubNav />
      </div>
      <div className="mt-3">
        <BandejaConciliacion />
      </div>
    </main>
  );
}
