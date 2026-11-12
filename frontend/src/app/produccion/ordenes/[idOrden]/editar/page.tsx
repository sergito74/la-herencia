"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";

import { ErrorState, LoadingState } from "@/components/ui/States";
import { OrdenForm } from "@/components/ordenes/OrdenForm";
import { PageHeader } from "@/components/ui/PageHeader";
import { fetchOrden } from "@/services/ordenesApi";

export default function EditarOrdenPage() {
  const { idOrden } = useParams<{ idOrden: string }>();
  const id = Number(idOrden);
  const { data: orden, isLoading, isError, refetch } = useQuery({ queryKey: ["orden", id], queryFn: () => fetchOrden(id) });

  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo={`Editar orden N° ${id}`} volver={`/produccion/ordenes/${id}`} />
      <div>
        {isLoading && <LoadingState />}
        {isError && <ErrorState message="No se pudo cargar la orden." onRetry={refetch} />}
        {orden && !orden.editable && <ErrorState message="Esta orden ya no se puede editar: tiene devoluciones, factura de contratista vinculada, o no está Planificada." />}
        {orden && orden.editable && <OrdenForm orden={orden} />}
      </div>
    </main>
  );
}
