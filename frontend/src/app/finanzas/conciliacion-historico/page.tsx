import { PageHeader } from "@/components/ui/PageHeader";
import { ConciliacionHistorica } from "@/components/conciliacion-historico/ConciliacionHistorica";

export const metadata = {
  title: "Conciliación histórica",
};

export default function ConciliacionHistoricaPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Conciliación histórica de cuentas corrientes" volver="/finanzas/cuentas-corrientes" ayuda="Resultado de aplicar retroactivamente el histórico de pagos y cobros (2015-2026) contra compras y ventas: qué quedó exacto, qué se aplicó con mejor esfuerzo, y qué necesita revisión manual (solo lectura)." />
      <div className="mt-3">
        <ConciliacionHistorica />
      </div>
    </main>
  );
}
