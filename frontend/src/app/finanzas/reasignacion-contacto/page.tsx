import { CandidatosReasignacion } from "@/components/reasignacion-contacto/CandidatosReasignacion";
import { HistorialReasignaciones } from "@/components/reasignacion-contacto/HistorialReasignaciones";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = {
  title: "Reasignación de contacto",
};

export default function ReasignacionContactoPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Reasignación de contacto</h1>
      <p className="mt-1 text-ink-secondary">
        Detección de movimientos bancarios cuyo contacto asignado no coincide con lo que indica su
        propia descripción, e historial de todas las reasignaciones aplicadas. Para corregir un
        movimiento puntual, usá el botón &quot;Reasignar&quot; desde la cuenta corriente del proveedor.
      </p>

      <section className="mt-6">
        <h2 className="text-lg font-semibold text-ink-primary">Candidatos a revisar</h2>
        <div className="mt-3">
          <CandidatosReasignacion />
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-ink-primary">Historial de reasignaciones</h2>
        <div className="mt-3">
          <HistorialReasignaciones />
        </div>
      </section>
    </main>
  );
}
