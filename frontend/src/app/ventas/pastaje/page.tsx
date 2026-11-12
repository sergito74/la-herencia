import { PageHeader } from "@/components/ui/PageHeader";
import { PastajeListado } from "@/components/pastaje/PastajeListado";

export const metadata = { title: "Pastaje" };

export default function PastajePage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Contratos de pastaje" ayuda="Hacienda de terceros en La Herencia: condiciones, bitácora, liquidación mensual por INMAG y facturas emitidas." />
      <div className="mt-3">
        <PastajeListado />
      </div>
    </main>
  );
}
