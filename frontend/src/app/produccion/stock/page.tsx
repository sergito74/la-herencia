"use client";

import { ExistenciasListado } from "@/components/stock/ExistenciasListado";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";

export default function Page() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <h1 className="text-2xl font-semibold">Existencias de insumos</h1>
      <div className="mt-4">
        <RemitosSubNav />
      </div>
      <div className="mt-6">
        <ExistenciasListado />
      </div>
    </main>
  );
}
