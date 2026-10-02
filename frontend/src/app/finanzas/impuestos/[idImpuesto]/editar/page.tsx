"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";

import { ImpuestoForm } from "@/components/impuestos/ImpuestoForm";
import { BackLink } from "@/components/ui/BackLink";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { fetchImpuesto } from "@/services/impuestosApi";

export default function EditarBoletaPage() {
  const params = useParams<{ idImpuesto: string }>();
  const idImpuesto = Number(params.idImpuesto);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["impuesto-detalle", idImpuesto],
    queryFn: () => fetchImpuesto(idImpuesto),
  });

  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/finanzas/impuestos">Volver a Impuestos</BackLink>
      <h1 className="mt-2 mb-4 text-2xl font-semibold">Editar boleta #{idImpuesto}</h1>
      {isLoading && <LoadingState />}
      {isError && <ErrorState message="No se pudo cargar la boleta." onRetry={() => refetch()} />}
      {data && <ImpuestoForm inicial={data} />}
    </main>
  );
}
