"use client";

import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";
import { ResultadoCultivoListado } from "@/components/ordenes/ResultadoCultivoListado";
import { BackLink } from "@/components/ui/BackLink";

export default function ResultadoCultivoPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/produccion/ordenes">Volver a Órdenes de trabajo</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Costo por cultivo / campaña</h1>
      <div className="mt-4">
        <RemitosSubNav />
      </div>
      <div className="mt-6">
        <ResultadoCultivoListado />
      </div>
    </main>
  );
}
