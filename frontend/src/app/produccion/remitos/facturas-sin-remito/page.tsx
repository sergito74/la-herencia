"use client";

import { FacturasSinRemitoListado } from "@/components/remitos/FacturasSinRemitoListado";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";
import { BackLink } from "@/components/ui/BackLink";

export default function Page() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/produccion/remitos">Volver a Remitos</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Facturas de insumos sin remito</h1>
      <div className="mt-4">
        <RemitosSubNav />
      </div>
      <div className="mt-6">
        <FacturasSinRemitoListado />
      </div>
    </main>
  );
}
