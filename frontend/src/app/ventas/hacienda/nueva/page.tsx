import { VentaHaciendaForm } from "@/components/ventas-hacienda/VentaHaciendaForm";

export const metadata = {
  title: "Nueva venta de hacienda",
};

export default function NuevaVentaHaciendaPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <VentaHaciendaForm mode="alta" />
    </main>
  );
}
