import { SaldosListado } from "@/components/cuentas-corrientes/SaldosListado";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = {
  title: "Saldos de cuentas corrientes",
};

export default function SaldosCuentasCorrientesPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/finanzas/cuentas-corrientes">Volver a Cuentas corrientes</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Saldos de cuentas corrientes</h1>
      <p className="mt-1 text-ink-secondary">
        Saldo actual de todos los proveedores con movimientos, incluidos los saldados en $0 (solo
        lectura).
      </p>
      <div className="mt-6">
        <SaldosListado />
      </div>
    </main>
  );
}
