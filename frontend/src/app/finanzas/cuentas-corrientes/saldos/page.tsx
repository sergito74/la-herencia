import { PageHeader } from "@/components/ui/PageHeader";
import { SaldosListado } from "@/components/cuentas-corrientes/SaldosListado";

export const metadata = {
  title: "Saldos de cuentas corrientes",
};

export default function SaldosCuentasCorrientesPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Saldos de cuentas corrientes" volver="/finanzas/cuentas-corrientes" ayuda="Saldo actual de todos los proveedores con movimientos, incluidos los saldados en $0 (solo lectura)." />
      <div className="mt-3">
        <SaldosListado />
      </div>
    </main>
  );
}
