"use client";

import { RemitosListado } from "@/components/remitos/RemitosListado";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";
import { BackLink } from "@/components/ui/BackLink";

export default function RemitosPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Remitos</h1>
      <div className="mt-4">
        <RemitosSubNav />
      </div>
      <div className="mt-6">
        <RemitosListado />
      </div>
    </main>
  );
}
