import { VentaHaciendaForm } from "@/components/ventas-hacienda/VentaHaciendaForm";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = {
  title: "Nueva venta de hacienda",
};

export default function NuevaVentaHaciendaPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <BackLink href="/ventas/hacienda">Volver a Ventas de hacienda</BackLink>
      <div className="mt-2">
        <VentaHaciendaForm mode="alta" />
      </div>
    </main>
  );
}
