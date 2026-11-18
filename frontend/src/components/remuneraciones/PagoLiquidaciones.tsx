"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { fetchSocios } from "@/services/cuentasSociosApi";
import { formatFecha, formatMoneda } from "@/lib/format";
import { pagarLiquidacionesCaja, pagarLiquidacionesSocio, pagarLiquidacionesTransferencia, previsualizarPagoLiquidaciones,
  transferenciasLiquidaciones, type PagoCajaLiquidacion, type PagoSocioLiquidacion, type PreviewPagoLiquidacion,
  type Remuneracion } from "@/services/remuneracionesApi";

const input = "rounded border border-border bg-white px-2 py-1.5 text-sm";
const boton = "rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken disabled:opacity-50";
const CAJAS = [["giamigli-sa", "Giamigli SA"], ["campo-chica", "Caja chica"]] as const;
const NOMBRE_CAJA: Record<string, string> = Object.fromEntries(CAJAS);
const BANCO: Record<string, string> = { galicia: "Galicia", bna: "Banco Nación" };
const MODOS = [["socio", "Lo pagó un socio"], ["banco", "Transferencia de Giamigli"], ["efectivo", "Efectivo de una caja"]] as const;
const hoy = () => new Date().toLocaleDateString("sv-SE");
export const faltaLiquidacion = (r: Remuneracion) => Math.max(0, Math.round(((r.importe ?? 0) - (r.pagado ?? 0)) * 100) / 100);

/** 18/11/2026: un solo pago para una o varias liquidaciones del mismo empleado. Queda un único egreso (asiento del
 * socio, débito del banco de Giamigli o pago de caja al empleado) vinculado a todas, de la más vieja a la más nueva. */
export function PagoLiquidaciones({ liquidaciones, onListo, cancelar }: { liquidaciones: Remuneracion[]; onListo: () => void; cancelar: () => void }) {
  const ids = liquidaciones.map(l => l.idSalario);
  const falta = Math.round(liquidaciones.reduce((s, l) => s + faltaLiquidacion(l), 0) * 100) / 100;
  const [modo, setModo] = useState<(typeof MODOS)[number][0]>("socio");
  const [socio, setSocio] = useState<PagoSocioLiquidacion>({ idSocio: 0, fecha: hoy(), importe: falta, medio: "" });
  const [datos, setDatos] = useState<PagoCajaLiquidacion>({ caja: "giamigli-sa", fecha: hoy(), importe: falta, cuenta: "B" });
  const [vista, setVista] = useState<PreviewPagoLiquidacion | null>(null);
  const [error, setError] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const socios = useQuery({ queryKey: ["cuentas-socios"], queryFn: fetchSocios, enabled: modo === "socio" });
  const banco = useQuery({ queryKey: ["liquidaciones-transferencias", ids], queryFn: () => transferenciasLiquidaciones(ids), enabled: modo === "banco" });
  const poner = (c: Partial<PagoCajaLiquidacion>) => { setDatos(d => ({ ...d, ...c })); setVista(null); };

  async function correr(fn: () => Promise<unknown>, terminar = true) {
    setOcupado(true); setError("");
    try { await fn(); if (terminar) onListo(); }
    catch (e) { setError(e instanceof Error ? e.message : "No se pudo registrar el pago"); }
    finally { setOcupado(false); }
  }

  return <section className="space-y-3 rounded-lg border border-border bg-surface p-4 text-sm">
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h2 className="text-base font-semibold">
        Pagar {liquidaciones.length === 1 ? "1 liquidación" : `${liquidaciones.length} liquidaciones`} de {liquidaciones[0].empleado} · falta {formatMoneda(falta)}
      </h2>
      <button className={boton} onClick={cancelar}>Cancelar</button>
    </div>
    <p className="text-ink-secondary">{liquidaciones.map(l => `${l.periodoLiquidado ?? formatFecha(l.fechaPago)} (${formatMoneda(faltaLiquidacion(l))})`).join(" · ")}</p>
    <div className="flex flex-wrap gap-2">
      {MODOS.map(([m, n]) => <button key={m} className={`${boton} ${modo === m ? "bg-surface-sunken font-medium" : ""}`}
        onClick={() => { setModo(m); setError(""); }}>{n}</button>)}
    </div>

    {modo === "socio" && <div className="space-y-2">
      <p className="text-ink-secondary">Un solo pago desde la cuenta personal del socio: queda a favor del socio en su cuenta, cancela el sueldo en la cuenta del empleado y queda vinculado a estas liquidaciones.</p>
      <div className="grid gap-2 md:grid-cols-4">
        <label>Socio<select className={`${input} block w-full`} value={socio.idSocio} onChange={e => { const id = Number(e.target.value); setSocio(s => ({ ...s, idSocio: id, medio: socios.data?.socios.find(x => x.idSocio === id)?.medios?.[0] ?? "" })); }}><option value={0}>Elegir</option>{socios.data?.socios.map(x => <option key={x.idSocio} value={x.idSocio}>{x.nombre}</option>)}</select></label>
        <label>Fecha<input type="date" className={`${input} block w-full`} value={socio.fecha} onChange={e => setSocio(s => ({ ...s, fecha: e.target.value }))} /></label>
        <label>Importe<MoneyInput className={`${input} block w-full`} moneda="Pesos" value={socio.importe} onChange={v => setSocio(s => ({ ...s, importe: v }))} /></label>
        <label>Desde<select className={`${input} block w-full`} value={socio.medio} onChange={e => setSocio(s => ({ ...s, medio: e.target.value }))}>{!socio.idSocio && <option value="">Elegí el socio</option>}{socios.data?.socios.find(x => x.idSocio === socio.idSocio)?.medios?.map(m => <option key={m}>{m}</option>)}</select></label>
      </div>
      <button className={boton} disabled={ocupado || !socio.idSocio || !socio.medio || !(socio.importe > 0)} onClick={() => correr(() => pagarLiquidacionesSocio(ids, socio))}>Registrar el pago</button>
    </div>}

    {modo === "banco" && <div className="space-y-2">
      <p className="text-ink-secondary">Transferencias de Giamigli al empleado ya cargadas del extracto, sin vincular. Elegí la que corresponde.</p>
      {banco.isLoading ? <p>Buscando transferencias…</p> : !banco.data?.length ? <p>No hay transferencias al empleado sin vincular. Aparecen cuando se carga el extracto del banco.</p> :
        banco.data.map(m => <div key={`${m.medio}-${m.id}`} className="flex flex-wrap items-center gap-3">
          <span>{formatFecha(m.fecha)} · {BANCO[m.medio] ?? m.medio}{m.detalle ? ` · ${m.detalle}` : ""}</span><strong>{formatMoneda(m.importe)}</strong>
          <button className={boton} disabled={ocupado} onClick={() => correr(() => pagarLiquidacionesTransferencia(ids, m.medio, m.id))}>Vincular este pago</button>
        </div>)}
    </div>}

    {modo === "efectivo" && <div className="space-y-2">
      <p className="text-ink-secondary">Sale de la caja como pago al empleado (el sueldo ya es costo por la liquidación: no se registra otro gasto).</p>
      <div className="grid gap-2 md:grid-cols-4">
        <label>Caja<select className={`${input} block w-full`} value={datos.caja} onChange={e => poner({ caja: e.target.value as PagoCajaLiquidacion["caja"] })}>{CAJAS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}</select></label>
        <label>Fecha<input type="date" className={`${input} block w-full`} value={datos.fecha} onChange={e => poner({ fecha: e.target.value })} /></label>
        <label>Importe<MoneyInput className={`${input} block w-full`} moneda="Pesos" value={datos.importe} onChange={v => poner({ importe: v })} /></label>
        <label>Cuenta<select className={`${input} block w-full`} value={datos.cuenta} onChange={e => poner({ cuenta: e.target.value as "A" | "B" })}><option value="A">A</option><option value="B">B</option></select></label>
      </div>
      {!vista ? <button className={boton} disabled={ocupado || !(datos.importe > 0)}
          onClick={() => correr(async () => setVista(await previsualizarPagoLiquidaciones(ids, datos)), false)}>Ver cómo queda la caja</button>
        : <div className="space-y-2">
          {vista.efectosPrevistos.map(e => <p key={e.caja}>Caja {NOMBRE_CAJA[e.caja] ?? e.caja}: sale {formatMoneda(-Number(e.importe))}, queda {formatMoneda(Number(e.saldoResultante))}.</p>)}
          {vista.advertencias.includes("SALDO_NEGATIVO") && <p className="text-status-warning">La caja queda en negativo.</p>}
          {vista.advertencias.includes("PERIODO_ARQUEADO") && <p className="text-status-warning">La fecha cae en un período con arqueo: el arqueo queda para rehacer.</p>}
          <button className={boton} disabled={ocupado} onClick={() => correr(() => pagarLiquidacionesCaja(ids, { ...datos, previewVersion: vista.previewVersion, advertenciasAceptadas: vista.advertencias }))}>Confirmar pago</button>
        </div>}
    </div>}
    {error && <p role="alert" className="text-status-danger">{error}</p>}
  </section>;
}
