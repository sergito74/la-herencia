"use client";

import Link from "next/link";

import { VentasHaciendaListado } from "@/components/ventas-hacienda/VentasHaciendaListado";

export default function VentasHaciendaPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Ventas de hacienda</h1>
        <Link
          href="/ventas/hacienda/nueva"
          className="rounded-sm bg-agro px-4 py-2 text-sm text-white hover:opacity-90"
        >
          + Nueva venta de hacienda
        </Link>
      </div>

      <div className="mt-6">
        <VentasHaciendaListado />
      </div>
    </main>
  );
}
