"use client";

import { OrdenForm } from "@/components/ordenes/OrdenForm";

export default function NuevaOrdenPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <h1 className="text-2xl font-semibold">Nueva orden de trabajo</h1>
      <div className="mt-6">
        <OrdenForm />
      </div>
    </main>
  );
}
