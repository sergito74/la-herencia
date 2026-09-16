import Link from "next/link";

import { DetalleCompra } from "@/components/compras/DetalleCompra";

export const metadata = {
  title: "Detalle de compra",
};

export default function CompraDetallePage({
  params,
}: {
  params: { idCompra: string };
}) {
  const idCompra = Number(params.idCompra);

  return (
    <main className="mx-auto max-w-6xl p-8">
      <Link className="text-sm text-finance underline" href="/compras">
        ← Volver al listado
      </Link>
      <h1 className="mt-2 text-2xl font-semibold">Detalle de compra</h1>
      <div className="mt-6">
        {Number.isFinite(idCompra) ? (
          <DetalleCompra idCompra={idCompra} />
        ) : (
          <p className="text-status-danger">Identificador de compra inválido.</p>
        )}
      </div>
    </main>
  );
}
