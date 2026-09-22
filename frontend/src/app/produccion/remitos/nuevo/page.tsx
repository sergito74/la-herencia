"use client";

import { Suspense } from "react";

import { RemitoForm } from "@/components/remitos/RemitoForm";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";
import { BackLink } from "@/components/ui/BackLink";

export default function NuevoRemitoPage() {
  return (
    <main className="mx-auto max-w-6xl px-8 py-6">
      <BackLink href="/produccion/remitos">Volver a Remitos</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Nuevo remito</h1>
      <div className="mt-4">
        <RemitosSubNav />
      </div>
      <p className="mt-3 text-xs text-ink-secondary">Al guardar, los productos suman al stock. El remito no lleva precio: el costo sale de la factura que vincules después.</p>
      <div className="mt-4">
        <Suspense fallback={null}>
          <RemitoForm />
        </Suspense>
      </div>
    </main>
  );
}
