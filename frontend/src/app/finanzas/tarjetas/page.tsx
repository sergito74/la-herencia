"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { TarjetasSaldos } from "@/components/tarjetas-cuenta/TarjetasSaldos";
import { TarjetasListado } from "@/components/tarjetas/TarjetasListado";
import { TarjetasSubNav } from "@/components/tarjetas/TarjetasSubNav";

export default function TarjetasPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Tarjetas" />
      <div>
        <TarjetasSubNav />
      </div>
      <div className="mt-4">
        <TarjetasSaldos />
      </div>
      <div className="mt-3">
        <TarjetasListado />
      </div>
    </main>
  );
}
