import { notFound } from "next/navigation";

import { CajaEfectivo } from "@/components/cajas-efectivo/CajaEfectivo";
import type { CajaSlug } from "@/services/cajasEfectivoApi";
import { BackLink } from "@/components/ui/BackLink";

const CAJAS_VALIDAS: CajaSlug[] = ["giamigli-sa", "campo-chica"];

export const metadata = {
  title: "Caja de efectivo",
};

export default function CajaEfectivoPage({ params }: { params: { caja: string } }) {
  const { caja } = params;
  if (!CAJAS_VALIDAS.includes(caja as CajaSlug)) {
    notFound();
  }

  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Caja de efectivo</h1>
      <p className="mt-1 text-ink-secondary">
        Historial y saldo migrados de &quot;Cajas Giamigli.xlsx&quot; — solo lectura.
      </p>
      <div className="mt-6">
        <CajaEfectivo caja={caja as CajaSlug} />
      </div>
    </main>
  );
}
