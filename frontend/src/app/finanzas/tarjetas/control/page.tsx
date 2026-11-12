"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { PanelCruces } from "@/components/tarjetas-cuenta/DialogoCruce";
import { PanelControl } from "@/components/tarjetas-cuenta/PanelControl";
import { TarjetasSubNav } from "@/components/tarjetas/TarjetasSubNav";

export default function ControlTarjetasPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Control de tarjetas" />
      <div>
        <TarjetasSubNav />
      </div>
      <div className="mt-3">
        <PanelControl />
      </div>
      <div className="mt-8">
        <PanelCruces />
      </div>
    </main>
  );
}
