"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { fetchCompraDetalle } from "@/services/tarjetasCuotasApi";
import { CompraCuotasForm } from "@/components/tarjetas-cuotas/CompraCuotasForm";
import { ErrorState, LoadingState } from "@/components/ui/States";

export default function EditarCompraCuotasPage() {
  const params = useParams<{ idPagoTarjeta: string }>();
  const idPagoTarjeta = Number(params.idPagoTarjeta);
  const router = useRouter();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tarjeta-cuotas-detalle-edicion", idPagoTarjeta],
    queryFn: () => fetchCompraDetalle(idPagoTarjeta),
  });

  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <button type="button" onClick={() => router.back()} className="text-sm text-finance underline">
        ← Volver a Compras en cuotas
      </button>
      <h1 className="mt-1 text-base font-semibold">Editar compra en cuotas</h1>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al cargar la compra." onRetry={() => refetch()} />}

      {data && (
        <div className="mt-2">
          <CompraCuotasForm mode="edicion" idPagoTarjeta={idPagoTarjeta} initial={data} />
        </div>
      )}
    </main>
  );
}
