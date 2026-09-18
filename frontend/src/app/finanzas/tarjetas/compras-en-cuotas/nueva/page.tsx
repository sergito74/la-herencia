import { CompraCuotasForm } from "@/components/tarjetas-cuotas/CompraCuotasForm";

export const metadata = {
  title: "Nueva compra en cuotas",
};

export default function NuevaCompraCuotasPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <CompraCuotasForm mode="alta" />
    </main>
  );
}
