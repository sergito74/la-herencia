import { redirect } from "next/navigation";

/** Una compra se ve y se corrige siempre en el formulario de carga y edición (pedido de Sergio, 27/10/2026). */
export default function CompraPage({ params }: { params: { idCompra: string } }) {
  redirect(`/compras/${params.idCompra}/editar`);
}
