import { ImpuestoForm } from "@/components/impuestos/ImpuestoForm";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = {
  title: "Nueva boleta de impuesto",
};

export default function NuevaBoletaPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/finanzas/impuestos">Volver a Impuestos</BackLink>
      <h1 className="mt-2 mb-4 text-2xl font-semibold">Nueva boleta de impuesto</h1>
      <ImpuestoForm />
    </main>
  );
}
