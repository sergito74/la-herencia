"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { UnidadesProductos } from "@/components/stock/UnidadesProductos";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";

export default function Page() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Unidades de productos" volver="/produccion/stock" pestanas={<RemitosSubNav grupo="existencias" />} />
      <div>
        <UnidadesProductos />
      </div>
    </main>
  );
}
