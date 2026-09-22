"use client";

import { OrdenForm } from "@/components/ordenes/OrdenForm";
import { BackLink } from "@/components/ui/BackLink";

export default function NuevaOrdenPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/produccion/ordenes">Volver a Órdenes de trabajo</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Nueva orden de trabajo</h1>
      <div className="mt-6">
        <OrdenForm />
      </div>
    </main>
  );
}
