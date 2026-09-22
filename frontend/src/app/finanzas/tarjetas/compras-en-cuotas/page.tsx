"use client";

import { ComprasCuotasListado } from "@/components/tarjetas-cuotas/ComprasCuotasListado";
import { TarjetasSubNav } from "@/components/tarjetas/TarjetasSubNav";
import { BackLink } from "@/components/ui/BackLink";

/** Solo lectura desde 2026-09-19 (feedback del usuario, punto 5) — la
 * estructura real (`[Tarjetas de Credito]`) es obsoleta, sin uso desde
 * 2015. Se conserva como catálogo histórico, sin alta. */
export default function ComprasCuotasPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/finanzas/tarjetas">Volver a Tarjetas</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Compras en cuotas (histórico)</h1>
      <p className="mt-1 text-xs text-ink-secondary">
        Catálogo de solo lectura — este mecanismo de financiación dejó de usarse en 2015. Las compras en cuotas
        vigentes (AgroNacion) se financian como líneas dentro del resumen mensual de la tarjeta.
      </p>
      <div className="mt-4">
        <TarjetasSubNav />
      </div>
      <div className="mt-6">
        <ComprasCuotasListado />
      </div>
    </main>
  );
}
