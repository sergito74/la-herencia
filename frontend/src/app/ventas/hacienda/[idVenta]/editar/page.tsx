"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { fetchVentaHaciendaDetalle } from "@/services/ventasHaciendaApi";
import { VentaHaciendaForm } from "@/components/ventas-hacienda/VentaHaciendaForm";
import { ErrorState, LoadingState } from "@/components/ui/States";

export default function EditarVentaHaciendaPage() {
  const params = useParams<{ idVenta: string }>();
  const idVenta = Number(params.idVenta);
  const router = useRouter();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["venta-hacienda-detalle-edicion", idVenta],
    queryFn: () => fetchVentaHaciendaDetalle(idVenta),
  });

  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => router.back()}
          title="Volver al listado de Ventas de Hacienda, con la búsqueda y el orden que tenía antes de entrar acá."
          className="text-sm text-finance underline"
        >
          ← Volver a Ventas de Hacienda
        </button>
      </div>
      <h1 className="mt-1 text-base font-semibold">Editar venta de hacienda</h1>

      {isLoading && <LoadingState />}
      {isError && (
        <ErrorState message="Ocurrió un error al cargar la venta." onRetry={() => refetch()} />
      )}

      {data && (
        <div className="mt-2">
          <VentaHaciendaForm mode="edicion" idVenta={idVenta} initial={data} />
        </div>
      )}
    </main>
  );
}
