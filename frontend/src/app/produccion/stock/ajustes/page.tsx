"use client";

import { AjustesListado } from "@/components/stock/AjustesListado";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";

export default function Page() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <h1 className="text-2xl font-semibold">Ajustes de inventario</h1>
      <div className="mt-4">
        <RemitosSubNav />
      </div>
      <div className="mt-6">
        <AjustesListado />
      </div>
    </main>
  );
}
