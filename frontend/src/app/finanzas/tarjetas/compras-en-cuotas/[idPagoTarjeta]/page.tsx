"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { fetchCompraDetalle } from "@/services/tarjetasCuotasApi";
import { formatMoneda } from "@/lib/format";
import { ErrorState, LoadingState } from "@/components/ui/States";

/** Solo lectura desde 2026-09-19 (feedback del usuario, punto 5) — la
 * estructura real es obsoleta (sin uso desde 2015), se conserva como
 * catálogo histórico. */
export default function CompraCuotasDetallePage() {
  const params = useParams<{ idPagoTarjeta: string }>();
  const idPagoTarjeta = Number(params.idPagoTarjeta);
  const router = useRouter();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tarjeta-cuotas-detalle", idPagoTarjeta],
    queryFn: () => fetchCompraDetalle(idPagoTarjeta),
  });

  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <button type="button" onClick={() => router.back()} className="text-sm text-finance underline">
        ← Volver a Compras en cuotas
      </button>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al cargar la compra." onRetry={() => refetch()} />}

      {data && (
        <div className="mt-2 space-y-3">
          <h1 className="text-base font-semibold">
            Compra en cuotas — {data.contacto ?? "—"} (comprobante {data.nroComprobante})
          </h1>
          <p className="text-xs text-ink-secondary">
            Fecha: {data.fecha} · {data.cantidadCuotas} cuotas · Total: {formatMoneda(data.importeTotal)}
          </p>
          <div className="rounded-md border border-border bg-surface p-2">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-ink-secondary">
                  <th className="py-1">Cuota</th>
                  <th className="py-1">Vencimiento</th>
                  <th className="py-1 text-right">Importe</th>
                  <th className="py-1 text-right">Estado</th>
                </tr>
              </thead>
              <tbody>
                {data.cuotas.map((c) => (
                  <tr key={c.idCuota} className="border-t border-border">
                    <td className="py-1">{c.numeroCuota}</td>
                    <td className="py-1">{c.fechaVencimiento}</td>
                    <td className="py-1 text-right font-data">{formatMoneda(c.importe)}</td>
                    <td className="py-1 text-right">{c.cobrado ? "Cobrada" : "Pendiente"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </main>
  );
}
