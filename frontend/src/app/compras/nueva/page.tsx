import { CompraForm } from "@/components/compras/CompraForm";

export const metadata = {
  title: "Nueva compra",
};

export default function NuevaCompraPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <CompraForm mode="alta" />
    </main>
  );
}
