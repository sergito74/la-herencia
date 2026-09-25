import { ConciliacionHistorica } from "@/components/conciliacion-historico/ConciliacionHistorica";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = {
  title: "Conciliación histórica",
};

export default function ConciliacionHistoricaPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/finanzas/cuentas-corrientes">Volver a Cuentas corrientes</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Conciliación histórica de cuentas corrientes</h1>
      <p className="mt-1 text-ink-secondary">
        Resultado de aplicar retroactivamente el histórico de pagos y cobros (2015-2026) contra
        compras y ventas: qué quedó exacto, qué se aplicó con mejor esfuerzo, y qué necesita
        revisión manual (solo lectura — corregir usa el mecanismo de aplicación de pagos existente).
      </p>
      <div className="mt-6">
        <ConciliacionHistorica />
      </div>
    </main>
  );
}
