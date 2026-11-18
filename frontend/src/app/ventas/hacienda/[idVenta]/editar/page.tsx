"use client";

import { PageHeader } from "@/components/ui/PageHeader";

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
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo={<>Editar venta de hacienda</>} onVolver={() => router.back()} />

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
