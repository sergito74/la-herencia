"use client";

import { PanelCruces } from "@/components/tarjetas-cuenta/DialogoCruce";
import { PanelControl } from "@/components/tarjetas-cuenta/PanelControl";
import { TarjetasSubNav } from "@/components/tarjetas/TarjetasSubNav";
import { BackLink } from "@/components/ui/BackLink";

export default function ControlTarjetasPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Control de tarjetas</h1>
      <div className="mt-4">
        <TarjetasSubNav />
      </div>
      <div className="mt-6">
        <PanelControl />
      </div>
      <div className="mt-8">
        <PanelCruces />
      </div>
    </main>
  );
}
