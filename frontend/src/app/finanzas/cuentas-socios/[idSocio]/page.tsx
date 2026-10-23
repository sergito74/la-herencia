import { CuentaSocio } from "@/components/cuentas-socios/CuentaSocio";
import { BackLink } from "@/components/ui/BackLink";
import { CajasNav } from "@/components/cajas-efectivo/CajasNav";

export const metadata = {
  title: "Cuenta corriente del socio",
};

export default function CuentaSocioPage({ params }: { params: { idSocio: string } }) {
  const { idSocio } = params;
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/finanzas/cajas">Volver a Cajas y socios</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">{idSocio === "3" ? "Condominio LSC — Cuenta con Giamigli" : "Cuenta corriente del socio"}</h1>
      <div className="mt-4"><CajasNav /></div>
      <div className="mt-6">
        <CuentaSocio idSocio={Number(idSocio)} />
      </div>
    </main>
  );
}
