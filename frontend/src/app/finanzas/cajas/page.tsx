import { CajasNav } from "@/components/cajas-efectivo/CajasNav";
import { CajasResumen } from "@/components/cajas-efectivo/CajasResumen";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = { title: "Cajas y socios" };

export default function CajasPage() {
  return (
    <main className="mx-auto max-w-none space-y-5 px-8 py-6">
      <div>
        <BackLink href="/">Volver al inicio</BackLink>
        <h1 className="mt-2 text-2xl font-semibold">Cajas y cuentas de socios</h1>
        <p className="mt-1 text-ink-secondary">Saldo de cada caja de efectivo y de la cuenta de cada socio. Elegí una para ver y cargar movimientos.</p>
      </div>
      <CajasNav />
      <CajasResumen />
    </main>
  );
}
