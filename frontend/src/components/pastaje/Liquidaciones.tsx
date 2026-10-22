"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";
import { formatFecha } from "@/lib/format";
import { API_BASE_URL } from "@/services/apiClient";
import {
  anularLiquidacion,
  confirmarLiquidacion,
  crearAjuste,
  crearLiquidacion,
  listarLiquidaciones,
  previewLiquidacion,
  urlPdfLiquidacion,
  type ContratoFicha,
  type Liquidacion,
  type Preview,
} from "@/services/pastajeApi";

import { btnPrimario, btnSecundario, indice, kg, mesTexto, pesos } from "./comunes";

function mesAnterior(): string {
  const d = new Date();
  d.setDate(1);
  d.setMonth(d.getMonth() - 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function Liquidaciones({ contrato, periodoInicial }: { contrato: ContratoFicha; periodoInicial?: string }) {
  const cache = useQueryClient();
  const { showToast } = useToast();
  const [periodo, setPeriodo] = useState(periodoInicial ?? mesAnterior());
  const prev = useQuery({ queryKey: ["pastaje", "preview", contrato.id, periodo], queryFn: () => previewLiquidacion(contrato.id, periodo) });
  const lista = useQuery({ queryKey: ["pastaje", "liquidaciones", contrato.id], queryFn: () => listarLiquidaciones(contrato.id) });
  const refrescar = () => cache.invalidateQueries({ queryKey: ["pastaje"] });
  const borrador = useMutation({ mutationFn: () => crearLiquidacion(contrato.id, periodo), onSuccess: refrescar });
  const confirmar = useMutation({
    mutationFn: (l: Liquidacion) => confirmarLiquidacion(l),
    onSuccess: (l) => {
      refrescar();
      showToast(`Liquidación confirmada. PDF guardado en ${l.archivoPdf}`, "success");
    },
  });
  const anular = useMutation({ mutationFn: (l: Liquidacion) => anularLiquidacion(l), onSuccess: refrescar });
  const ajuste = useMutation({ mutationFn: (id: number) => crearAjuste(id), onSuccess: refrescar });
  const p = prev.data;
  const liq = p?.liquidacion ?? null;
  const enCurso = periodo >= new Date().toISOString().slice(0, 7);
  const mes = contrato.meses.find((m) => m.periodo.startsWith(periodo));
  const motivoBloqueo = p?.bloqueo ?? (enCurso ? "Mes en curso: se liquida a mes vencido." : !p?.tramos.length ? "No hubo hacienda en el campo ese mes." : null);
  const error = borrador.error ?? confirmar.error ?? anular.error ?? ajuste.error;

  const copiar = async (texto: string) => {
    await navigator.clipboard.writeText(texto);
    showToast("Texto copiado para ARCA", "success");
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          Mes a liquidar
          <input type="month" className="ml-2 rounded-sm border border-border bg-surface px-2 py-1" value={periodo} onChange={(e) => setPeriodo(e.target.value)} />
        </label>
        {liq && <StatusBadge label={liq.estado === "borrador" ? "Borrador" : "Confirmada"} tone={liq.estado === "borrador" ? "warning" : "success"} />}
      </div>

      {prev.isLoading && <LoadingState />}
      {prev.isError && <ErrorState message={(prev.error as Error).message} onRetry={() => prev.refetch()} />}
      {p && <Detalle p={p} liq={liq} />}

      {p && (
        <SoloLectura>
          <div className="flex flex-wrap items-center gap-3">
            {!liq && (
              <button className={btnPrimario} disabled={!!motivoBloqueo || borrador.isPending} aria-describedby="motivo-bloqueo" onClick={() => borrador.mutate()}>
                Preparar borrador
              </button>
            )}
            {liq?.estado === "borrador" && (
              <>
                <button className={btnSecundario} onClick={() => borrador.mutate()} disabled={borrador.isPending}>Recalcular borrador</button>
                <button className={btnPrimario} disabled={!!p.bloqueo || confirmar.isPending} aria-describedby="motivo-bloqueo" onClick={() => confirmar.mutate(liq)}>
                  {confirmar.isPending ? "Confirmando…" : "Confirmar y generar PDF"}
                </button>
                <button className={btnSecundario} onClick={() => anular.mutate(liq)}>Descartar borrador</button>
              </>
            )}
            {liq?.estado === "confirmada" && mes?.diferencia && (
              <button className={btnPrimario} onClick={() => ajuste.mutate(liq.id)}>
                Preparar ajuste por {pesos(mes.diferencia)}
              </button>
            )}
            {motivoBloqueo && !liq && <span id="motivo-bloqueo" className="text-sm text-ink-secondary">{motivoBloqueo}</span>}
          </div>
        </SoloLectura>
      )}
      {error && <p role="alert" className="text-sm text-status-danger">{(error as Error).message}</p>}

      {p && p.textoFactura.length > 0 && liq?.estado === "confirmada" && (
        <section className="rounded-md border border-border bg-surface p-4">
          <h3 className="font-semibold">Para emitir en ARCA</h3>
          {p.textoFactura.map((t) => (
            <p key={t} className="mt-2 flex items-center gap-3 text-sm">
              <span className="font-data">{t}</span>
              <button className="text-xs underline" onClick={() => copiar(t)}>Copiar</button>
            </p>
          ))}
          <p className="mt-2 text-sm">Neto {pesos(liq.neto)} · IVA 21% {pesos(liq.iva)} · Total {pesos(liq.total)} · Contado</p>
        </section>
      )}

      <section>
        <h3 className="mb-2 font-semibold">Historial de liquidaciones</h3>
        {lista.data?.length ? (
          <table className="min-w-full text-sm">
            <thead className="text-left text-xs uppercase text-ink-secondary">
              <tr>
                <th className="py-1">Mes</th><th>Tipo</th><th>Estado</th><th className="text-right">Neto</th><th className="text-right">Total</th><th>PDF</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {lista.data.map((l) => (
                <tr key={l.id} className={l.estado === "anulada" ? "text-ink-secondary line-through" : ""}>
                  <td className="py-1 capitalize">
                    <button className="underline" onClick={() => setPeriodo(l.periodo.slice(0, 7))}>{mesTexto(l.periodo)}</button>
                  </td>
                  <td>{l.tipo === "ajuste" ? "Ajuste" : "Mensual"}</td>
                  <td>{l.estado}</td>
                  <td className="font-data text-right tabular-nums">{pesos(l.neto)}</td>
                  <td className="font-data text-right tabular-nums">{pesos(l.total)}</td>
                  <td>
                    {l.archivoPdf && (
                      <a className="underline" href={`${API_BASE_URL}${urlPdfLiquidacion(l.id)}`} target="_blank" rel="noreferrer">Abrir</a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-ink-secondary">Sin liquidaciones todavía.</p>
        )}
      </section>
    </div>
  );
}

function Detalle({ p, liq }: { p: Preview; liq: Liquidacion | null }) {
  const fijada = liq?.estado === "confirmada" ? liq : null;
  const tramos = fijada?.tramos ?? p.tramos;
  const indices = fijada?.indices ?? p.indices;
  const v = fijada ?? p;
  if (p.bloqueo && !fijada) {
    return <p role="alert" className="rounded-sm bg-status-danger-bg px-3 py-2 text-sm text-status-danger">{p.bloqueo} Cargalo a mano en la pestaña Índice INMAG.</p>;
  }
  if (!tramos.length) return null;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="rounded-md border border-border bg-surface p-4">
        <h3 className="font-semibold">Proporción temporal {fijada ? "(fijada al confirmar)" : "(cálculo vigente)"}</h3>
        <table className="mt-2 min-w-full text-sm">
          <thead className="text-left text-xs uppercase text-ink-secondary">
            <tr><th className="py-1">Tramo</th><th className="text-right">Cabezas</th><th className="text-right">Días</th><th className="text-right">Kg / importe</th></tr>
          </thead>
          <tbody className="divide-y divide-border">
            {tramos.map((t, i) => (
              <tr key={i}>
                <td className="py-1">{t.categoria} · {formatFecha(t.desde)} al {formatFecha(t.hasta)}</td>
                <td className="font-data text-right tabular-nums">{t.cabezas}</td>
                <td className="font-data text-right tabular-nums">{t.dias}{p.diasMes ? ` de ${p.diasMes}` : ""}</td>
                <td className="font-data text-right tabular-nums">{t.tipoTarifa === "kg_novillo" ? kg(t.kg) : pesos(t.importe)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {v.kg && Number(v.kg) > 0 && <p className="mt-2 text-sm">Total: <span className="font-data">{kg(v.kg)} de novillo</span></p>}
      </section>
      <section className="rounded-md border border-border bg-surface p-4">
        <h3 className="font-semibold">Valorización (INMAG Cañuelas)</h3>
        <ul className="mt-2 text-sm">
          {indices.map((i) => (
            <li key={i.fecha} className="flex justify-between border-b border-border py-1">
              <span>{formatFecha(i.fecha)}</span>
              <span className="font-data tabular-nums">{indice(i.indice)}</span>
            </li>
          ))}
        </ul>
        <dl className="mt-3 grid grid-cols-2 gap-y-1 text-sm">
          <dt>Precio promedio</dt><dd className="font-data text-right">{indice(v.precioPromedio)}</dd>
          <dt>Neto</dt><dd className="font-data text-right">{pesos(v.neto)}</dd>
          <dt>IVA 21%</dt><dd className="font-data text-right">{pesos(v.iva)}</dd>
          <dt className="font-semibold">Total</dt><dd className="font-data text-right font-semibold">{pesos(v.total)}</dd>
        </dl>
      </section>
    </div>
  );
}
