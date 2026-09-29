import { CuentaSocio } from "@/components/cuentas-socios/CuentaSocio";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = {
  title: "Cuenta corriente del socio",
};

export default function CuentaSocioPage({ params }: { params: { idSocio: string } }) {
  const { idSocio } = params;
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/finanzas/cuentas-socios">Volver a Cuentas de socios</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Cuenta corriente del socio</h1>
      <div className="mt-6">
        <CuentaSocio idSocio={Number(idSocio)} />
      </div>
    </main>
  );
}
