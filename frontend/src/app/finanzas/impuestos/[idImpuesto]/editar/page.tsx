"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";

import { ImpuestoForm } from "@/components/impuestos/ImpuestoForm";
import { ImpuestoParticularPanel } from "@/components/impuestos/ImpuestoParticularPanel";
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
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo={`Editar boleta #${idImpuesto}`} volver="/finanzas/impuestos" />
      {isLoading && <LoadingState />}
      {isError && <ErrorState message="No se pudo cargar la boleta." onRetry={() => refetch()} />}
      {data && <ImpuestoForm inicial={data} />}
      {data && <ImpuestoParticularPanel idImpuesto={idImpuesto} />}
    </main>
  );
}
