"use client";

import { BajasListado } from "@/components/stock/BajasListado";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";

export default function Page() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <h1 className="text-2xl font-semibold">Bajas de stock</h1>
      <div className="mt-4">
        <RemitosSubNav />
      </div>
      <div className="mt-6">
        <BajasListado />
      </div>
    </main>
  );
}
