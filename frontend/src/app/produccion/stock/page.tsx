"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { ExistenciasListado } from "@/components/stock/ExistenciasListado";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";

export default function Page() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Existencias de insumos" pestanas={<RemitosSubNav grupo="existencias" />} />
      <div>
        <ExistenciasListado />
      </div>
    </main>
  );
}
