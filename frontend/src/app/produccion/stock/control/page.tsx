"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { ControlCierre } from "@/components/stock/ControlCierre";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";

export default function Page() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Control de cierre de insumos" volver="/produccion/stock" />
      <div>
        <RemitosSubNav grupo="existencias" />
      </div>
      <div className="mt-3">
        <ControlCierre />
      </div>
    </main>
  );
}
