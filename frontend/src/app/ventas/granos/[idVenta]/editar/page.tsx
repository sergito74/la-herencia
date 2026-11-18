"use client";

import { PageHeader } from "@/components/ui/PageHeader";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { fetchVentaGranosDetalle } from "@/services/ventasGranosApi";
import { VentaGranosForm } from "@/components/ventas-granos/VentaGranosForm";
import { ErrorState, LoadingState } from "@/components/ui/States";

export default function EditarVentaGranosPage() {
  const params = useParams<{ idVenta: string }>();
  const idVenta = Number(params.idVenta);
  const router = useRouter();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["venta-granos-detalle-edicion", idVenta],
    queryFn: () => fetchVentaGranosDetalle(idVenta),
  });

  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo={<>Editar venta de granos</>} onVolver={() => router.back()} />

      {isLoading && <LoadingState />}
      {isError && (
        <ErrorState message="Ocurrió un error al cargar la venta." onRetry={() => refetch()} />
      )}

      {data && (
        <div className="mt-2">
          <VentaGranosForm mode="edicion" idVenta={idVenta} initial={data} />
        </div>
      )}
    </main>
  );
}
