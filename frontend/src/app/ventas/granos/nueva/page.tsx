import { VentaGranosForm } from "@/components/ventas-granos/VentaGranosForm";

export const metadata = {
  title: "Nueva venta de granos",
};

export default function NuevaVentaGranosPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <VentaGranosForm mode="alta" />
    </main>
  );
}
