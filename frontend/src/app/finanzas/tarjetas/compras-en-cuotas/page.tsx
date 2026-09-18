"use client";

import Link from "next/link";

import { ComprasCuotasListado } from "@/components/tarjetas-cuotas/ComprasCuotasListado";

export default function ComprasCuotasPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Compras en cuotas</h1>
        <Link href="/finanzas/tarjetas/compras-en-cuotas/nueva" className="rounded-sm bg-finance px-4 py-2 text-sm text-white hover:opacity-90">
          + Nueva compra en cuotas
        </Link>
      </div>
      <div className="mt-6">
        <ComprasCuotasListado />
      </div>
    </main>
  );
}
