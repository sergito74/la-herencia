"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { RemitosListado } from "@/components/remitos/RemitosListado";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";

export default function RemitosPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Remitos" />
      <div>
        <RemitosSubNav grupo="remitos" />
      </div>
      <div className="mt-3">
        <RemitosListado />
      </div>
    </main>
  );
}
