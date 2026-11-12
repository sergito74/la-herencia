import { PageHeader } from "@/components/ui/PageHeader";
import { CajasNav } from "@/components/cajas-efectivo/CajasNav";
import { CajasResumen } from "@/components/cajas-efectivo/CajasResumen";

export const metadata = { title: "Cajas y socios" };

export default function CajasPage() {
  return (
    <main className="mx-auto max-w-none space-y-3 px-6 py-3">
      <div>
        <PageHeader titulo="Cajas y cuentas de socios" ayuda="Saldo de cada caja de efectivo y de la cuenta de cada socio. Elegí una para ver y cargar movimientos." />
      </div>
      <CajasNav />
      <CajasResumen />
    </main>
  );
}
