"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { ComprasCuotasListado } from "@/components/tarjetas-cuotas/ComprasCuotasListado";
import { TarjetasSubNav } from "@/components/tarjetas/TarjetasSubNav";

/** Solo lectura desde 2026-09-19 (feedback del usuario, punto 5) — la
 * estructura real (`[Tarjetas de Credito]`) es obsoleta, sin uso desde
 * 2015. Se conserva como catálogo histórico, sin alta. */
export default function ComprasCuotasPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Compras en cuotas (histórico)" volver="/finanzas/tarjetas" ayuda="Catálogo de solo lectura — este mecanismo de financiación dejó de usarse en 2015. Las compras en cuotas vigentes (AgroNacion) se financian como líneas dentro del resumen mensual de la tarjeta." />
      <div>
        <TarjetasSubNav />
      </div>
      <div className="mt-3">
        <ComprasCuotasListado />
      </div>
    </main>
  );
}
