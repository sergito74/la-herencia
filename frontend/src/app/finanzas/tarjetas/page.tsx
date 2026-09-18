"use client";

import { TarjetasListado } from "@/components/tarjetas/TarjetasListado";

export default function TarjetasPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <h1 className="text-2xl font-semibold">Tarjetas</h1>
      <div className="mt-6">
        <TarjetasListado />
      </div>
    </main>
  );
}
