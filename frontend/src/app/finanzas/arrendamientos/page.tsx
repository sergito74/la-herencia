import { ArrendamientosListado } from "@/components/arrendamientos/ArrendamientosListado";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = {
  title: "Arrendamientos",
};

export default function ArrendamientosPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Arrendamientos</h1>
      <p className="mt-1 text-ink-secondary">
        Contratos de arrendamiento y sus cobros asociados (solo lectura).
      </p>
      <div className="mt-6">
        <ArrendamientosListado />
      </div>
    </main>
  );
}
