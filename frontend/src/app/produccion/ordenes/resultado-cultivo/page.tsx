"use client";

import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";
import { ResultadoCultivoListado } from "@/components/ordenes/ResultadoCultivoListado";

export default function ResultadoCultivoPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <h1 className="text-2xl font-semibold">Costo por cultivo / campaña</h1>
      <div className="mt-4">
        <RemitosSubNav />
      </div>
      <div className="mt-6">
        <ResultadoCultivoListado />
      </div>
    </main>
  );
}
