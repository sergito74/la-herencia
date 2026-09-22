import { CuentaCorriente } from "@/components/cuentas-corrientes/CuentaCorriente";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = {
  title: "Cuentas corrientes",
};

export default function CuentasCorrientesPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Cuentas corrientes</h1>
      <p className="mt-1 text-ink-secondary">
        Buscar un contacto y ver su saldo y movimientos (solo lectura).
      </p>
      <div className="mt-6">
        <CuentaCorriente />
      </div>
    </main>
  );
}
