import { PageHeader } from "@/components/ui/PageHeader";
import { ArrendamientosListado } from "@/components/arrendamientos/ArrendamientosListado";

export const metadata = {
  title: "Arrendamientos",
};

export default function ArrendamientosPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Arrendamientos" ayuda="Contratos de arrendamiento y sus cobros asociados (solo lectura)." />
      <div className="mt-3">
        <ArrendamientosListado />
      </div>
    </main>
  );
}
