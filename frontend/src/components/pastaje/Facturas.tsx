"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { ArchivoVinculado } from "@/components/ui/ArchivoVinculado";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatFecha } from "@/lib/format";
import { API_BASE_URL } from "@/services/apiClient";
import {
  anularComprobante,
  leerComprobante,
  listarComprobantes,
  listarLiquidaciones,
  registrarComprobante,
  urlPdfComprobante,
  urlPdfLiquidacion,
  type Comprobante,
  type ComprobanteLeido,
  type ContratoFicha,
  type Liquidacion,
} from "@/services/pastajeApi";

import { btnPrimario, btnSecundario, inputCls, mesTexto, pesos } from "./comunes";

const TIPO = { factura: "Factura", nota_debito: "Nota de débito", nota_credito: "Nota de crédito" } as const;
const numero = (c: { letra: string; puntoVenta: number; numero: number }) =>
  `${c.letra} ${String(c.puntoVenta).padStart(4, "0")}-${String(c.numero).padStart(8, "0")}`;

export function Facturas({ contrato }: { contrato: ContratoFicha }) {
  const comps = useQuery({ queryKey: ["pastaje", "comprobantes", contrato.id], queryFn: () => listarComprobantes(contrato.id) });
  const liqs = useQuery({ queryKey: ["pastaje", "liquidaciones", contrato.id], queryFn: () => listarLiquidaciones(contrato.id) });
  const [cargar, setCargar] = useState(false);
  const [anular, setAnular] = useState<Comprobante | null>(null);

  if (comps.isLoading || liqs.isLoading) return <LoadingState />;
  if (comps.isError) return <ErrorState message={(comps.error as Error).message} onRetry={() => comps.refetch()} />;
  const confirmadas = (liqs.data ?? []).filter((l) => l.estado === "confirmada");
  const lista = comps.data ?? [];
  const sinFactura = confirmadas.filter((l) => l.tipo === "mensual" && !lista.some((c) => c.idLiquidacion === l.id && c.tipo === "factura" && c.estado === "vigente"));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-secondary">
          Facturas emitidas en ARCA. Se cargan desde el PDF; las correcciones van con ND/NC vinculadas, sin tocar la factura.
        </p>
        <SoloLectura>
          <button className={btnPrimario} disabled={!confirmadas.length} aria-describedby="motivo-sin-liquidacion" onClick={() => setCargar(true)}>
            + Cargar comprobante desde PDF
          </button>
        </SoloLectura>
      </div>
      {!confirmadas.length && (
        <p id="motivo-sin-liquidacion" role="status" className="rounded-sm bg-status-warning-bg px-3 py-2 text-sm text-status-warning">
          Para cargar una factura primero tiene que haber una liquidación confirmada del mes: registrá el ingreso de la hacienda en
          Bitácora y después preparala y confirmala en Liquidaciones. La factura se vincula a esa liquidación.
        </p>
      )}
      {sinFactura.length > 0 && (
        <p role="status" className="rounded-sm bg-status-warning-bg px-3 py-2 text-sm text-status-warning">
          ⚠ Liquidaciones confirmadas sin factura: {sinFactura.map((l) => mesTexto(l.periodo)).join(", ")}.
        </p>
      )}
      {lista.length === 0 ? (
        <EmptyState message="Todavía no hay comprobantes cargados." />
      ) : (
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="min-w-full text-sm">
            <thead className="bg-surface-muted text-left text-xs uppercase text-ink-secondary">
              <tr>
                <th className="px-3 py-2">Mes</th><th className="px-3 py-2">Comprobante</th><th className="px-3 py-2">Fecha</th>
                <th className="px-3 py-2 text-right">Neto</th><th className="px-3 py-2 text-right">Total</th>
                <th className="px-3 py-2 text-right">Cobrado</th><th className="px-3 py-2 text-right">Saldo</th><th className="px-3 py-2">PDF</th><th />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {lista.map((c) => {
                const l = liqs.data?.find((x) => x.id === c.idLiquidacion) ?? liqs.data?.find((x) => x.id === lista.find((f) => f.id === c.idComprobanteAsociado)?.idLiquidacion);
                return (
                  <tr key={c.id} className={c.estado === "anulado" ? "text-ink-secondary line-through" : ""}>
                    <td className="px-3 py-2 capitalize">{l ? mesTexto(l.periodo) : "—"}</td>
                    <td className="px-3 py-2">{TIPO[c.tipo]} {numero(c)}{c.cae && <span className="block text-xs text-ink-secondary">CAE {c.cae}</span>}</td>
                    <td className="px-3 py-2">{formatFecha(c.fecha)}</td>
                    <td className="font-data px-3 py-2 text-right tabular-nums">{pesos(c.tipo === "nota_credito" ? -Number(c.neto) : c.neto)}</td>
                    <td className="font-data px-3 py-2 text-right tabular-nums">{pesos(c.tipo === "nota_credito" ? -Number(c.total) : c.total)}</td>
                    <td className="font-data px-3 py-2 text-right tabular-nums">{c.tipo === "nota_credito" ? "—" : pesos(c.cobrado)}</td>
                    <td className="px-3 py-2 text-right">
                      {c.tipo === "nota_credito" || c.estado === "anulado" ? "—" : Number(c.saldo) <= 0.005 ? <StatusBadge label="Cobrado" tone="success" /> : <span className="font-data tabular-nums">{pesos(c.saldo)}</span>}
                    </td>
                    <td className="px-3 py-2">
                      {c.archivoPdf && <a className="underline" target="_blank" rel="noreferrer" href={`${API_BASE_URL}${urlPdfComprobante(c.id)}`}>Factura</a>}
                      {l?.archivoPdf && <a className="ml-2 underline" target="_blank" rel="noreferrer" href={`${API_BASE_URL}${urlPdfLiquidacion(l.id)}`}>Liquidación</a>}
                    </td>
                    <td className="px-3 py-2">
                      {c.estado === "vigente" && Number(c.cobrado) === 0 && (
                        <SoloLectura><button className="text-xs underline" onClick={() => setAnular(c)}>Anular</button></SoloLectura>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-ink-secondary">El cobro se registra desde Tesorería, Cajas de efectivo o cheques, aplicándolo a la factura de pastaje en la cuenta corriente del cliente (incluye retenciones sufridas).</p>

      <SideDrawer open={cargar} onClose={() => setCargar(false)} title="Cargar comprobante emitido" maxWidthClass="max-w-3xl">
        <CargaComprobante contrato={contrato} liqs={confirmadas} comps={lista} onListo={() => setCargar(false)} />
      </SideDrawer>
      <SideDrawer open={anular !== null} onClose={() => setAnular(null)} title="Anular comprobante">
        {anular && <AnularForm c={anular} onListo={() => setAnular(null)} />}
      </SideDrawer>
    </div>
  );
}

function AnularForm({ c, onListo }: { c: Comprobante; onListo: () => void }) {
  const cache = useQueryClient();
  const [motivo, setMotivo] = useState("");
  const m = useMutation({ mutationFn: () => anularComprobante(c, motivo), onSuccess: () => { cache.invalidateQueries({ queryKey: ["pastaje"] }); onListo(); } });
  return (
    <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <p className="text-sm">{TIPO[c.tipo]} {numero(c)} por {pesos(c.total)}. Solo para comprobantes cargados por error y sin cobros.</p>
      <label className="block text-sm">Motivo<input autoFocus required className={inputCls} value={motivo} onChange={(e) => setMotivo(e.target.value)} /></label>
      {m.error && <p role="alert" className="text-sm text-status-danger">{(m.error as Error).message}</p>}
      <button className={btnSecundario} disabled={!motivo || m.isPending}>Anular</button>
    </form>
  );
}

function CargaComprobante({ contrato, liqs, comps, onListo }: { contrato: ContratoFicha; liqs: Liquidacion[]; comps: Comprobante[]; onListo: () => void }) {
  const cache = useQueryClient();
  const [ruta, setRuta] = useState("");
  const [leido, setLeido] = useState<ComprobanteLeido | null>(null);
  const [idLiq, setIdLiq] = useState<number | null>(null);
  const [idAsoc, setIdAsoc] = useState<number | null>(null);
  const [acepto, setAcepto] = useState(false);
  const leer = useMutation({
    mutationFn: () => leerComprobante(ruta),
    onSuccess: (d) => {
      setLeido(d);
      setAcepto(false);
      if (d.tipo === "factura") {
        const libre = liqs.find((l) => l.tipo === "mensual" && Number(l.total) === Number(d.total) && !comps.some((c) => c.idLiquidacion === l.id && c.estado === "vigente"));
        setIdLiq(libre?.id ?? null);
      } else {
        setIdLiq(null);
      }
    },
  });
  const guardar = useMutation({
    mutationFn: () => {
      const { cuitEmisor: _e, cliente: _c, advertencias: _a, ...datos } = leido!;
      void _e; void _c; void _a;
      return registrarComprobante({ ...datos, idContrato: contrato.id, idLiquidacion: idLiq, idComprobanteAsociado: leido!.tipo === "factura" ? null : idAsoc, aceptarAdvertencias: acepto });
    },
    onSuccess: () => {
      cache.invalidateQueries({ queryKey: ["pastaje"] });
      onListo();
    },
  });
  const liq = liqs.find((l) => l.id === idLiq);
  const difs: string[] = [...(leido?.advertencias ?? [])];
  if (leido && liq) {
    (["neto", "iva", "total"] as const).forEach((k) => {
      const esperado = Math.abs(Number(liq[k]));
      if (Math.abs(Number(leido[k]) - esperado) > 0.001) difs.push(`${k.toUpperCase()}: comprobante ${pesos(leido[k])} · liquidación ${pesos(esperado)}`);
    });
  }
  if (leido?.cuitCliente && contrato.cuit && leido.cuitCliente !== contrato.cuit.replace(/-/g, "")) difs.push(`CUIT del cliente distinto (${leido.cuitCliente}).`);
  const opcionesLiq = leido?.tipo === "factura" ? liqs.filter((l) => l.tipo === "mensual") : liqs.filter((l) => l.tipo === "ajuste");
  const facturas = comps.filter((c) => c.tipo === "factura" && c.estado === "vigente");
  const listo = leido && (leido.tipo === "factura" ? idLiq : idAsoc) && (difs.length === 0 || acepto);

  return (
    <div className="space-y-4">
      <ol className="list-decimal space-y-4 pl-5 text-sm">
        <li>
          <ArchivoVinculado label="PDF del comprobante (ARCA)" value={ruta} onChange={(r) => { setRuta(r); setLeido(null); }} inputClassName={inputCls} />
          <button className={`${btnSecundario} mt-2`} disabled={!ruta || leer.isPending} onClick={() => leer.mutate()}>
            {leer.isPending ? "Leyendo…" : "Leer PDF"}
          </button>
          {leer.error && <p role="alert" className="mt-1 text-status-danger">{(leer.error as Error).message}</p>}
        </li>
        {leido && (
          <li className="space-y-3">
            <p className="font-semibold">{TIPO[leido.tipo]} {numero(leido)} del {formatFecha(leido.fecha)} · CAE {leido.cae}</p>
            <p className="text-ink-secondary">{leido.cliente} · CUIT {leido.cuitCliente} · {leido.detalle}</p>
            <label className="block">
              {leido.tipo === "factura" ? "Liquidación del mes" : "Liquidación de ajuste (opcional)"}
              <select className={inputCls} value={idLiq ?? ""} onChange={(e) => setIdLiq(e.target.value ? Number(e.target.value) : null)}>
                <option value="">—</option>
                {opcionesLiq.map((l) => <option key={l.id} value={l.id}>{mesTexto(l.periodo)} · total {pesos(l.total)}</option>)}
              </select>
            </label>
            {leido.tipo !== "factura" && (
              <label className="block">
                Factura que corrige
                <select className={inputCls} value={idAsoc ?? ""} onChange={(e) => setIdAsoc(e.target.value ? Number(e.target.value) : null)}>
                  <option value="">—</option>
                  {facturas.map((f) => <option key={f.id} value={f.id}>{numero(f)} · {pesos(f.total)}</option>)}
                </select>
              </label>
            )}
            <table className="min-w-full">
              <thead className="text-left text-xs uppercase text-ink-secondary"><tr><th /><th className="text-right">Comprobante</th><th className="text-right">Liquidación</th></tr></thead>
              <tbody className="divide-y divide-border">
                {(["neto", "iva", "total"] as const).map((k) => (
                  <tr key={k}>
                    <td className="py-1 capitalize">{k === "iva" ? "IVA" : k}</td>
                    <td className="font-data text-right tabular-nums">{pesos(leido[k])}</td>
                    <td className="font-data text-right tabular-nums">{liq ? pesos(Math.abs(Number(liq[k]))) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {difs.length > 0 ? (
              <div role="alert" className="rounded-sm bg-status-warning-bg p-3 text-status-warning">
                <ul className="list-disc pl-4">{difs.map((d) => <li key={d}>{d}</li>)}</ul>
                <label className="mt-2 flex items-center gap-2"><input type="checkbox" checked={acepto} onChange={(e) => setAcepto(e.target.checked)} /> Revisé las diferencias y quiero guardarlo igual</label>
              </div>
            ) : (
              <p className="text-status-success">✓ Coincide con la liquidación y el contrato.</p>
            )}
          </li>
        )}
      </ol>
      {guardar.error && <p role="alert" className="text-sm text-status-danger">{(guardar.error as Error).message}</p>}
      <button className={btnPrimario} disabled={!listo || guardar.isPending} onClick={() => guardar.mutate()}>
        {guardar.isPending ? "Guardando…" : "Guardar comprobante"}
      </button>
    </div>
  );
}
