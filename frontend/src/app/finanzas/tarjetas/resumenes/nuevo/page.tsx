import { ResumenForm } from "@/components/tarjetas-resumenes/ResumenForm";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = {
  title: "Nuevo resumen de tarjeta",
};

export default function NuevoResumenPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <BackLink href="/finanzas/tarjetas/resumenes">Volver a Resúmenes</BackLink>
      <div className="mt-2">
        <ResumenForm mode="alta" />
      </div>
    </main>
  );
}
