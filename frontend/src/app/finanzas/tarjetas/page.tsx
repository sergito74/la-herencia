"use client";

import { TarjetasListado } from "@/components/tarjetas/TarjetasListado";
import { TarjetasSubNav } from "@/components/tarjetas/TarjetasSubNav";
import { BackLink } from "@/components/ui/BackLink";

export default function TarjetasPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Tarjetas</h1>
      <div className="mt-4">
        <TarjetasSubNav />
      </div>
      <div className="mt-6">
        <TarjetasListado />
      </div>
    </main>
  );
}
