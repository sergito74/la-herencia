"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { fetchResumenDetalle } from "@/services/tarjetasResumenesApi";
import { formatMoneda } from "@/lib/format";
import { ErrorState, LoadingState } from "@/components/ui/States";

export default function ResumenDetallePage() {
  const params = useParams<{ idResumen: string }>();
  const idResumen = Number(params.idResumen);
  const router = useRouter();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tarjeta-resumen-detalle", idResumen],
    queryFn: () => fetchResumenDetalle(idResumen),
  });

  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <button type="button" onClick={() => router.back()} className="text-sm text-finance underline">
        ← Volver
      </button>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al cargar el resumen." onRetry={() => refetch()} />}

      {data && (
        <div className="mt-2 space-y-3">
          <div className="flex items-center justify-between">
            <h1 className="text-base font-semibold">
              Resumen {data.codigo} — {data.tarjeta}
            </h1>
            <Link href={`/finanzas/tarjetas/resumenes/${idResumen}/editar`} className="text-sm text-finance underline">
              Editar
            </Link>
          </div>
          <p className="text-xs text-ink-secondary">
            Cierre: {data.fechaCierre} · Vencimiento: {data.fechaVencimiento}
          </p>
          <p className="font-data text-sm font-semibold">Total calculado: {formatMoneda(data.totalCalculado)}</p>

          <div className="rounded-md border border-border bg-surface p-2">
            <h2 className="text-xs font-medium text-ink-secondary">
              Líneas de consumo {data.lineas.length === 0 && "(ninguna — solo cabecera)"}
            </h2>
            {data.lineas.length > 0 && (
              <table className="mt-1 w-full text-xs">
                <thead>
                  <tr className="text-left text-ink-secondary">
                    <th className="py-1">Fecha</th>
                    <th className="py-1">Detalle</th>
                    <th className="py-1 text-right">Importe</th>
                  </tr>
                </thead>
                <tbody>
                  {data.lineas.map((l) => (
                    <tr key={l.idLineaConsumo} className="border-t border-border">
                      <td className="py-1">{l.fechaCompra}</td>
                      <td className="py-1">{l.detalle}</td>
                      <td className="py-1 text-right font-data">{formatMoneda(l.importe)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
