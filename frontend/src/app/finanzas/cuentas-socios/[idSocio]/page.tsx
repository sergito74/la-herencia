import { PageHeader } from "@/components/ui/PageHeader";
import { CuentaSocio } from "@/components/cuentas-socios/CuentaSocio";
import { CajasNav } from "@/components/cajas-efectivo/CajasNav";

export const metadata = {
  title: "Cuenta corriente del socio",
};

export default function CuentaSocioPage({ params }: { params: { idSocio: string } }) {
  const { idSocio } = params;
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo={idSocio === "3" ? "Condominio LSC — Cuenta con Giamigli" : "Cuenta corriente del socio"} volver="/finanzas/cajas" />
      <div><CajasNav /></div>
      <div className="mt-3">
        <CuentaSocio idSocio={Number(idSocio)} />
      </div>
    </main>
  );
}
