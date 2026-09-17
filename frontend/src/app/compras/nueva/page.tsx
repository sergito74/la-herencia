import { CompraForm } from "@/components/compras/CompraForm";

export const metadata = {
  title: "Nueva compra",
};

export default function NuevaCompraPage() {
  return (
    <main className="mx-auto max-w-[100rem] px-8 py-3">
      <CompraForm mode="alta" />
    </main>
  );
}
