"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { formatFecha, formatMoneda } from "@/lib/format";
import { revisionCuentasApi, type Cola, type EstadoEfectivo, type Etapa } from "@/services/revisionCuentasApi";
import { NOMBRE_COLA } from "./ColaCuentas";
import { ListaPreguntas } from "./ListaPreguntas";

const COLAS: Cola[] = ["H", "D", "E", "C", "G", "F", "I", "B", "A"];   // en el orden de precedencia
const ETAPAS: Etapa[] = ["E0", "E1", "E2", "E3", "E4", "E5", "E6"];
const NOMBRE_ETAPA: Record<Etapa, string> = {
  E0: "Fuentes", E1: "Documentos", E2: "Movimientos", E3: "Tarjetas", E4: "Evidencia", E5: "FIFO", E6: "Cierre",
};
const NOMBRE_ESTADO: Record<EstadoEfectivo, string> = {
  pendiente: "Pendientes",
  "en-proceso": "En proceso",
  "esperando-evidencia": "Esperando evidencia",
  "esperando-sergio": "Esperando a Sergio",
  cerrada: "Cerradas",
  "cerrada-con-excepcion": "Cerradas con excepción",
  reabierta: "Reabiertas",
};

/**
 * Tablero de la revisión de cuentas: cuántas cuentas hay en cada cola y etapa y cuánto dinero está en juego, el avance contra la semana
 * anterior y las preguntas que bloquean cuentas. Cada cola abre la lista de sus cuentas y su lote.
 */
export function TableroColas() {
  const { data, isLoading, isFetching, error, refetch } = useQuery({ queryKey: ["revision-tablero"], queryFn: () => revisionCuentasApi.tablero() });

  if (isLoading) return <p className="text-sm text-ink-secondary">Calculando el tablero de las cuentas… (la primera vez puede tardar unos segundos)</p>;
  if (error || !data) return <p role="alert" className="text-sm text-status-danger">No se pudo calcular el tablero.</p>;

  const celda = (cola: Cola, etapa: Etapa) => data.casillas.find((c) => c.cola === cola && c.etapa === etapa);
  const cerradas = (data.porEstado.cerrada ?? 0) + (data.porEstado["cerrada-con-excepcion"] ?? 0);
  const excepciones = data.totalesPorCola.I?.cuentas ?? 0;

  return (
    <div className="space-y-5 text-sm">
      <section className="space-y-1">
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
          <span>Corte: <b>{formatFecha(data.corte)}</b></span>
          <span><b>{data.totalCuentas}</b> cuentas</span>
          <span><b>{cerradas}</b> cerradas</span>
          <span>Cola de excepciones: <b>{excepciones}</b> ({data.totalCuentas ? ((excepciones / data.totalCuentas) * 100).toFixed(1).replace(".", ",") : "0"} %)</span>
          <button type="button" onClick={() => refetch()} disabled={isFetching} className="rounded border border-line px-2 py-0.5 text-xs">
            {isFetching ? "Actualizando…" : "Actualizar"}
          </button>
        </div>
        {data.comparacion ? (
          <p className="text-xs text-ink-secondary">
            Contra la semana del {formatFecha(data.comparacion.semanaAnterior)}: {data.comparacion.cerradasEnLaSemana >= 0 ? "+" : ""}{data.comparacion.cerradasEnLaSemana} cuentas
            cerradas · la cola de excepciones {data.comparacion.variacionExcepciones > 0 ? "creció" : data.comparacion.variacionExcepciones < 0 ? "bajó" : "no cambió"}
            {data.comparacion.variacionExcepciones !== 0 ? ` en ${Math.abs(data.comparacion.variacionExcepciones)}` : ""}.
          </p>
        ) : (
          <p className="text-xs text-ink-secondary">Todavía no hay una foto de la semana anterior para comparar el avance.</p>
        )}
      </section>

      <section>
        <h2 className="mb-1 font-semibold">Colas por etapas</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-ink-secondary">
                <th className="py-1">Cola</th>
                {ETAPAS.map((e) => <th key={e} className="text-right">{e} {NOMBRE_ETAPA[e]}</th>)}
                <th className="text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {COLAS.map((cola) => {
                const total = data.totalesPorCola[cola];
                if (!total) return null;
                return (
                  <tr key={cola} className="border-t border-line">
                    <td className="py-1">
                      <Link className="text-finance underline" href={`/finanzas/revision-cuentas/cola/${cola}`}>{cola}: {NOMBRE_COLA[cola]}</Link>
                    </td>
                    {ETAPAS.map((e) => {
                      const c = celda(cola, e);
                      return (
                        <td key={e} className="text-right" title={c ? `${c.cuentas} cuentas · ${formatMoneda(c.importe)} en juego` : undefined}>
                          {c ? <><b>{c.cuentas}</b><br /><span className="text-ink-secondary">{formatMoneda(c.importe)}</span></> : "—"}
                        </td>
                      );
                    })}
                    <td className="text-right"><b>{total.cuentas}</b><br /><span className="text-ink-secondary">{formatMoneda(total.importe)}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="mt-1 text-xs text-ink-secondary">Cada cuenta figura en una sola casilla. El importe es lo que está en juego: el mayor entre su saldo y los pagos sin factura que faltan respaldar.</p>
      </section>

      <section>
        <h2 className="mb-1 font-semibold">Por estado</h2>
        <ul className="flex flex-wrap gap-2 text-xs">
          {(Object.keys(NOMBRE_ESTADO) as EstadoEfectivo[]).map((e) => (
            <li key={e} className="rounded border border-line px-2 py-1">{NOMBRE_ESTADO[e]}: <b>{data.porEstado[e] ?? 0}</b></li>
          ))}
        </ul>
      </section>

      <ListaPreguntas />
    </div>
  );
}
