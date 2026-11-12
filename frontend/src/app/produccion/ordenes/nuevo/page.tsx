"use client";

import { OrdenForm } from "@/components/ordenes/OrdenForm";
import { PageHeader } from "@/components/ui/PageHeader";

export default function NuevaOrdenPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Nueva orden de trabajo" volver="/produccion/ordenes" />
      <OrdenForm />
    </main>
  );
}
