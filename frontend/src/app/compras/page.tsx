import { ComprasListado } from "@/components/compras/ComprasListado";

export const metadata = {
  title: "Compras",
};

export default function ComprasPage() {
  return (
    <main className="mx-auto max-w-6xl p-8">
      <h1 className="text-2xl font-semibold">Compras</h1>
      <p className="mt-1 text-slate-600">
        Buscar y listar compras (solo lectura).
      </p>
      <div className="mt-6">
        <ComprasListado />
      </div>
    </main>
  );
}
