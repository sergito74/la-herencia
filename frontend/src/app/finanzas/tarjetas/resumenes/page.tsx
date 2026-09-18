"use client";

import Link from "next/link";

import { ResumenesListado } from "@/components/tarjetas-resumenes/ResumenesListado";
import { TarjetasSubNav } from "@/components/tarjetas/TarjetasSubNav";

export default function ResumenesPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Resúmenes de tarjeta</h1>
        <Link href="/finanzas/tarjetas/resumenes/nuevo" className="rounded-sm bg-finance px-4 py-2 text-sm text-white hover:opacity-90">
          + Nuevo resumen
        </Link>
      </div>
      <div className="mt-4">
        <TarjetasSubNav />
      </div>
      <div className="mt-6">
        <ResumenesListado />
      </div>
    </main>
  );
}
