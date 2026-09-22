"use client";

import { RemitosListado } from "@/components/remitos/RemitosListado";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";

export default function RemitosPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <h1 className="text-2xl font-semibold">Remitos</h1>
      <div className="mt-4">
        <RemitosSubNav />
      </div>
      <div className="mt-6">
        <RemitosListado />
      </div>
    </main>
  );
}
