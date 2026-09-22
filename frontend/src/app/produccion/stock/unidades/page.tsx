"use client";

import { UnidadesProductos } from "@/components/stock/UnidadesProductos";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";

export default function Page() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <h1 className="text-2xl font-semibold">Unidades de productos</h1>
      <div className="mt-4">
        <RemitosSubNav />
      </div>
      <div className="mt-6">
        <UnidadesProductos />
      </div>
    </main>
  );
}
