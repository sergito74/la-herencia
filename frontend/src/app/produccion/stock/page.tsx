"use client";

import { ExistenciasListado } from "@/components/stock/ExistenciasListado";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";
import { BackLink } from "@/components/ui/BackLink";

export default function Page() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Existencias de insumos</h1>
      <div className="mt-4">
        <RemitosSubNav />
      </div>
      <div className="mt-6">
        <ExistenciasListado />
      </div>
    </main>
  );
}
