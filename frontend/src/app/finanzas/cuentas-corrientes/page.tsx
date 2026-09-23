import Link from "next/link";

import { CuentaCorriente } from "@/components/cuentas-corrientes/CuentaCorriente";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = {
  title: "Cuentas corrientes",
};

export default function CuentasCorrientesPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <div className="mt-2 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Cuentas corrientes</h1>
          <p className="mt-1 text-ink-secondary">
            Buscar un contacto y ver su saldo y movimientos (solo lectura).
          </p>
        </div>
        <Link
          href="/finanzas/cuentas-corrientes/saldos"
          className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken"
        >
          Ver saldos de todos los proveedores
        </Link>
      </div>
      <div className="mt-6">
        <CuentaCorriente />
      </div>
    </main>
  );
}
