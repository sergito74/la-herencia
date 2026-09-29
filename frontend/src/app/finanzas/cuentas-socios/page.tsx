import { SociosListado } from "@/components/cuentas-socios/SociosListado";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = {
  title: "Cuentas de socios",
};

export default function CuentasSociosPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Cuentas de socios</h1>
      <p className="mt-1 text-ink-secondary">
        Cuenta corriente de cada socio/director y del condominio: gastos particulares pagados por
        la empresa que les corresponden a ellos, y devoluciones/compensaciones registradas.
      </p>
      <div className="mt-6">
        <SociosListado />
      </div>
    </main>
  );
}
