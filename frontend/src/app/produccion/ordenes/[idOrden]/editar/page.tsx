"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";

import { ErrorState, LoadingState } from "@/components/ui/States";
import { OrdenForm } from "@/components/ordenes/OrdenForm";
import { fetchOrden } from "@/services/ordenesApi";

export default function EditarOrdenPage() {
  const { idOrden } = useParams<{ idOrden: string }>();
  const id = Number(idOrden);
  const { data: orden, isLoading, isError, refetch } = useQuery({ queryKey: ["orden", id], queryFn: () => fetchOrden(id) });

  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <h1 className="text-2xl font-semibold">Editar orden N° {id}</h1>
      <div className="mt-6">
        {isLoading && <LoadingState />}
        {isError && <ErrorState message="No se pudo cargar la orden." onRetry={refetch} />}
        {orden && !orden.editable && <ErrorState message="Esta orden ya no se puede editar: tiene devoluciones, factura de contratista vinculada, o no está Planificada." />}
        {orden && orden.editable && <OrdenForm orden={orden} />}
      </div>
    </main>
  );
}
