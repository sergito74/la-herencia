"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { FacturasSinRemitoListado } from "@/components/remitos/FacturasSinRemitoListado";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";

export default function Page() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Facturas de insumos sin remito" volver="/produccion/remitos" />
      <div>
        <RemitosSubNav grupo="remitos" />
      </div>
      <div className="mt-3">
        <FacturasSinRemitoListado />
      </div>
    </main>
  );
}
