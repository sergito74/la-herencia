import { PageHeader } from "@/components/ui/PageHeader";
import Link from "next/link";

import { CuentaCorriente } from "@/components/cuentas-corrientes/CuentaCorriente";
import { Suspense } from "react";
import { NuevosParaRevisar } from "@/components/documentos-nuevos/NuevosParaRevisar";

export const metadata = {
  title: "Cuentas corrientes",
};

export default function CuentasCorrientesPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <Suspense fallback={null}>
        <NuevosParaRevisar modulo="cuentas_corrientes" />
      </Suspense>
      <PageHeader titulo="Cuentas corrientes" ayuda="Buscar un contacto y ver su saldo y movimientos (solo lectura).">
          <Link
            href="/finanzas/cuentas-corrientes/saldos"
            className="rounded border border-border px-3 py-1 text-sm hover:bg-surface-sunken"
          >
            Ver saldos de todos los proveedores
          </Link>
          <Link
            href="/finanzas/conciliacion-historico"
            className="rounded border border-border px-3 py-1 text-sm hover:bg-surface-sunken"
          >
            Conciliación histórica
          </Link>
      </PageHeader>
      <div>
        <CuentaCorriente />
      </div>
    </main>
  );
}
