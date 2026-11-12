"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import Link from "next/link";

import { ResumenesListado } from "@/components/tarjetas-resumenes/ResumenesListado";
import { TarjetasSubNav } from "@/components/tarjetas/TarjetasSubNav";
import { SoloLectura } from "@/components/auth/SoloLectura";

export default function ResumenesPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Resúmenes de tarjeta" volver="/finanzas/tarjetas">
        <SoloLectura>
          <Link href="/finanzas/tarjetas/resumenes/nuevo" className="rounded-sm bg-finance px-3 py-1 text-sm text-white hover:opacity-90">
            + Nuevo resumen
          </Link>
        </SoloLectura>
      </PageHeader>
      <div>
        <TarjetasSubNav />
      </div>
      <div className="mt-3">
        <ResumenesListado />
      </div>
    </main>
  );
}
