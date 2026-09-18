import { ResumenForm } from "@/components/tarjetas-resumenes/ResumenForm";

export const metadata = {
  title: "Nuevo resumen de tarjeta",
};

export default function NuevoResumenPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <ResumenForm mode="alta" />
    </main>
  );
}
