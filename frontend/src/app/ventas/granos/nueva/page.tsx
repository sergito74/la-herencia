import { VentaGranosForm } from "@/components/ventas-granos/VentaGranosForm";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = {
  title: "Nueva venta de granos",
};

export default function NuevaVentaGranosPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <BackLink href="/ventas/granos">Volver a Ventas de granos</BackLink>
      <div className="mt-2">
        <VentaGranosForm mode="alta" />
      </div>
    </main>
  );
}
