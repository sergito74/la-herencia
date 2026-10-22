import { PastajeListado } from "@/components/pastaje/PastajeListado";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = { title: "Pastaje" };

export default function PastajePage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Contratos de pastaje</h1>
      <p className="mt-1 text-ink-secondary">
        Hacienda de terceros en La Herencia: condiciones, bitácora, liquidación mensual por INMAG y facturas emitidas.
      </p>
      <div className="mt-6">
        <PastajeListado />
      </div>
    </main>
  );
}
