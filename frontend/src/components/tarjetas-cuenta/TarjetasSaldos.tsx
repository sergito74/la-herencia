"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatMoneda } from "@/lib/format";
import { fetchResumenTarjetas } from "@/services/tarjetasCuentaApi";

/** Saldo de la cuenta de cada tarjeta (034, FR-008/FR-009). Negativo = se debe. */
export function TarjetasSaldos() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tarjetas-cuenta-resumen"],
    queryFn: () => fetchResumenTarjetas(),
  });
  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState message="No se pudieron cargar los saldos de las tarjetas." onRetry={() => refetch()} />;

  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold text-ink-primary">Lo que se debe a cada tarjeta</h2>
      {data.tarjetasSinContacto.length > 0 && (
        <p role="alert" className="rounded border border-status-danger px-3 py-2 text-xs text-status-danger">
          Tarjetas sin cuenta asociada: {data.tarjetasSinContacto.map((t) => t.tarjeta).join(", ")}.
        </p>
      )}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-ink-secondary">
            <th className="py-1">Tarjeta</th>
            <th className="text-right">Deuda</th>
            <th className="text-right">Pagos y devoluciones</th>
            <th className="text-right">Saldo</th>
            <th className="text-right">Último movimiento</th>
          </tr>
        </thead>
        <tbody>
          {data.tarjetas.map((t) => (
            <tr key={t.idTarjeta} className="border-t border-line">
              <td className="py-1">
                <Link className="text-finance underline" href={`/finanzas/tarjetas/${t.idTarjeta}/cuenta-corriente`}>
                  {t.tarjeta}
                </Link>
                {t.diferenciaConModuloTarjetas != null && t.diferenciaConModuloTarjetas >= 1 && (
                  <span className="ml-2 text-xs text-status-danger">
                    no coincide con el módulo de tarjetas ({formatMoneda(t.diferenciaConModuloTarjetas)})
                  </span>
                )}
              </td>
              <td className="text-right">{formatMoneda(t.deuda)}</td>
              <td className="text-right">{formatMoneda(t.credito)}</td>
              <td className="text-right font-medium">{formatMoneda(t.saldo)}</td>
              <td className="text-right">{formatFecha(t.ultimoMovimiento)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t border-line font-semibold">
            <td className="py-1">Total</td>
            <td className="text-right">{formatMoneda(data.total.deuda)}</td>
            <td className="text-right">{formatMoneda(data.total.credito)}</td>
            <td className="text-right">{formatMoneda(data.total.saldo)}</td>
            <td />
          </tr>
        </tfoot>
      </table>
      <p className="text-xs text-ink-secondary">{data.avisoSaldo}</p>
    </section>
  );
}
