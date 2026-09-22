"use client";

import { BandejaConciliacion } from "@/components/tarjetas-conciliacion/BandejaConciliacion";
import { TarjetasSubNav } from "@/components/tarjetas/TarjetasSubNav";
import { BackLink } from "@/components/ui/BackLink";

export default function ConciliacionPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/finanzas/tarjetas">Volver a Tarjetas</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Conciliación de consumos</h1>
      <div className="mt-4">
        <TarjetasSubNav />
      </div>
      <div className="mt-6">
        <BandejaConciliacion />
      </div>
    </main>
  );
}
