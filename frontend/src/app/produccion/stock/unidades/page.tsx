"use client";

import { UnidadesProductos } from "@/components/stock/UnidadesProductos";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";
import { BackLink } from "@/components/ui/BackLink";

export default function Page() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/produccion/stock">Volver a Existencias de insumos</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Unidades de productos</h1>
      <div className="mt-4">
        <RemitosSubNav />
      </div>
      <div className="mt-6">
        <UnidadesProductos />
      </div>
    </main>
  );
}
