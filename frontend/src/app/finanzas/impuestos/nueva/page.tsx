import { PageHeader } from "@/components/ui/PageHeader";
import { ImpuestoForm } from "@/components/impuestos/ImpuestoForm";

export const metadata = {
  title: "Nueva boleta de impuesto",
};

export default function NuevaBoletaPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Nueva boleta de impuesto" volver="/finanzas/impuestos" />
      <ImpuestoForm />
    </main>
  );
}
