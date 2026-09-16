import { CuentaCorriente } from "@/components/cuentas-corrientes/CuentaCorriente";

export const metadata = {
  title: "Cuentas corrientes",
};

export default function CuentasCorrientesPage() {
  return (
    <main className="mx-auto max-w-6xl p-8">
      <h1 className="text-2xl font-semibold">Cuentas corrientes</h1>
      <p className="mt-1 text-slate-600">
        Buscar un contacto y ver su saldo y movimientos (solo lectura).
      </p>
      <div className="mt-6">
        <CuentaCorriente />
      </div>
    </main>
  );
}
