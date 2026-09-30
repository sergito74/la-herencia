import { CasosARevisar } from "@/components/migracion-cajas-giamigli/CasosARevisar";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = {
  title: "Migración Cajas Giamigli — revisión",
};

export default function MigracionCajasGiamigliRevisionPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Casos a revisar — Cajas Giamigli</h1>
      <p className="mt-1 text-ink-secondary">
        Filas de la planilla &quot;Cajas Giamigli.xlsx&quot; que no se pudieron migrar automáticamente
        con confianza (sin fecha, sin importe, etc.) — ninguna se pierde en silencio.
      </p>
      <div className="mt-6">
        <CasosARevisar />
      </div>
    </main>
  );
}
