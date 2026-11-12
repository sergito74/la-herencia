import { PageHeader } from "@/components/ui/PageHeader";
import { CasosARevisar } from "@/components/migracion-cajas-giamigli/CasosARevisar";

export const metadata = {
  title: "Migración Cajas Giamigli — revisión",
};

export default function MigracionCajasGiamigliRevisionPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Casos a revisar — Cajas Giamigli" ayuda="Filas de la planilla &quot;Cajas Giamigli.xlsx&quot; que no se pudieron migrar automáticamente con confianza (sin fecha, sin importe, etc.) — ninguna se pierde en silencio." />
      <div className="mt-3">
        <CasosARevisar />
      </div>
    </main>
  );
}
