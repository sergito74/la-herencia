"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { AjustesListado } from "@/components/stock/AjustesListado";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";

export default function Page() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Ajustes de inventario" volver="/produccion/stock" />
      <div>
        <RemitosSubNav grupo="existencias" />
      </div>
      <div className="mt-3">
        <AjustesListado />
      </div>
    </main>
  );
}
