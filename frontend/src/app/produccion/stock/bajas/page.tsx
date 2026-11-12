"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { BajasListado } from "@/components/stock/BajasListado";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";

export default function Page() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Bajas de stock" volver="/produccion/stock" />
      <div>
        <RemitosSubNav grupo="existencias" />
      </div>
      <div className="mt-3">
        <BajasListado />
      </div>
    </main>
  );
}
