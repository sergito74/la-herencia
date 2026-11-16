"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";
import { VinculosPropuestosListado } from "@/components/remitos/VinculosPropuestosListado";

export default function Page() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Vínculos remito ↔ factura propuestos" volver="/produccion/remitos" />
      <div>
        <RemitosSubNav grupo="remitos" />
      </div>
      <div className="mt-3">
        <VinculosPropuestosListado />
      </div>
    </main>
  );
}
