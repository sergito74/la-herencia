import { ArrendamientosListado } from "@/components/arrendamientos/ArrendamientosListado";

export const metadata = {
  title: "Arrendamientos",
};

export default function ArrendamientosPage() {
  return (
    <main className="mx-auto max-w-6xl p-8">
      <h1 className="text-2xl font-semibold">Arrendamientos</h1>
      <p className="mt-1 text-ink-secondary">
        Contratos de arrendamiento y sus cobros asociados (solo lectura).
      </p>
      <div className="mt-6">
        <ArrendamientosListado />
      </div>
    </main>
  );
}
