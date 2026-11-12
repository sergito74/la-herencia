"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { fetchCompraDetalle } from "@/services/comprasApi";
import { CompraForm } from "@/components/compras/CompraForm";
import { compraDetalleAInput } from "@/components/compras/compraDetalleAInput";
import { ErrorState, LoadingState } from "@/components/ui/States";

export default function EditarCompraPage() {
  const params = useParams<{ idCompra: string }>();
  const idCompra = Number(params.idCompra);
  const router = useRouter();

  // Siempre la versión guardada (12/11/2026): el formulario toma sus valores al abrirse, así que una copia vieja en
  // caché pisaba lo último guardado (ej. importes de las cuotas).
  const { data, isLoading, isFetching, isError, refetch } = useQuery({
    queryKey: ["compra-detalle-edicion", idCompra],
    queryFn: () => fetchCompraDetalle(idCompra),
    staleTime: 0,
    gcTime: 0,
    refetchOnMount: "always",
  });

  return (
    <main className="mx-auto max-w-none px-6 py-2">
      <div className="flex items-baseline gap-4">
        <h1 className="text-base font-semibold">Editar compra</h1>
        <button
          type="button"
          onClick={() => router.back()}
          title="Volver al listado de Compras, con la búsqueda y el orden que tenía antes de entrar acá."
          className="text-sm text-finance underline"
        >
          ← Volver a Compras
        </button>
      </div>

      {isLoading && <LoadingState />}
      {isError && (
        <ErrorState message="Ocurrió un error al cargar la compra." onRetry={() => refetch()} />
      )}

      {data && (
        <div className="mt-1">
          <CompraForm
            mode="edicion"
            idCompra={idCompra}
            initial={compraDetalleAInput(data, idCompra)}
            proveedorNombreInicial={data.proveedor?.razonSocial ?? null}
          />
        </div>
      )}
    </main>
  );
}
