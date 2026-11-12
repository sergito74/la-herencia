"use client";

import { ResultadoCultivoListado } from "@/components/ordenes/ResultadoCultivoListado";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";

export default function ResultadoCultivoPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <h1 className="text-2xl font-semibold">Imputación de costos</h1>
      <div className="mt-4"><RemitosSubNav grupo="costos" /></div>
      <h2 className="mt-4 text-lg font-medium">Costo por cultivo / campaña</h2>
      <div className="mt-4">
        <ResultadoCultivoListado />
      </div>
    </main>
  );
}
