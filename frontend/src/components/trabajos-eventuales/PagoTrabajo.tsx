"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { fetchFiltrosCompras } from "@/services/comprasApi";
import { formatFecha, formatMoneda } from "@/lib/format";
import { pagarTrabajoCaja, pagarTrabajoTransferencia, previsualizarPagoTrabajo, quitarPagoTrabajo,
  transferenciasTrabajo, type PagoCajaInput, type PreviewPagoTrabajo, type Trabajo } from "@/services/trabajosEventualesApi";

const input = "rounded border border-border bg-white px-2 py-1.5 text-sm";
const boton = "rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken disabled:opacity-50";
const CAJAS = [["giamigli-sa", "Giamigli SA"], ["campo-chica", "Caja chica"], ["condominio-lsc", "Condominio LSC"]] as const;
const NOMBRE_CAJA: Record<string, string> = Object.fromEntries(CAJAS);
const BANCO: Record<string, string> = { galicia: "Galicia", bna: "Banco Nación" };
const hoy = () => new Date().toISOString().slice(0, 10);

/** Pago de un trabajo eventual (04/11/2026): en efectivo sale de una caja como gasto sin comprobante (descuenta su
 * saldo); por transferencia se vincula al movimiento del banco ya cargado. El recibo no es obligatorio. */
export function PagoTrabajo({ t, onCambio }: { t: Trabajo; onCambio: () => Promise<void> }) {
  const falta = Math.max(0, Math.round((t.total - (t.pagado ?? 0)) * 100) / 100);
  const [modo, setModo] = useState<"" | "efectivo" | "transferencia">("");
  const [datos, setDatos] = useState<PagoCajaInput>({ caja: "giamigli-sa", fecha: hoy(), importe: falta, cuenta: "B", idRubro: 0, idCentroCostos: 0, idCampania: null });
  const [vista, setVista] = useState<PreviewPagoTrabajo | null>(null);
  const [error, setError] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const catalogos = useQuery({ queryKey: ["compras-filtros"], queryFn: fetchFiltrosCompras, enabled: modo === "efectivo" });
  const transfer = useQuery({ queryKey: ["trabajo-transferencias", t.idTrabajo], queryFn: () => transferenciasTrabajo(t.idTrabajo), enabled: modo === "transferencia" });
  const poner = (c: Partial<PagoCajaInput>) => { setDatos(d => ({ ...d, ...c })); setVista(null); };

  async function correr(fn: () => Promise<unknown>, cerrar = true) {
    setOcupado(true); setError("");
    try { await fn(); if (cerrar) { setModo(""); setVista(null); } await onCambio(); }
    catch (e) { setError(e instanceof Error ? e.message : "No se pudo completar el pago"); }
    finally { setOcupado(false); }
  }

  async function previsualizar() {
    setOcupado(true); setError("");
    try { setVista(await previsualizarPagoTrabajo(t.idTrabajo, datos)); }
    catch (e) { setError(e instanceof Error ? e.message : "No se pudo previsualizar"); }
    finally { setOcupado(false); }
  }

  return <div className="space-y-2">
    <h3 className="font-medium">Pagos</h3>
    {t.pagos?.length ? t.pagos.map(p => <div key={p.idPago} className="flex flex-wrap items-center gap-3 text-sm">
      <span>{formatFecha(p.fecha)} · {p.medio === "caja" ? `Efectivo, caja ${NOMBRE_CAJA[p.caja ?? ""] ?? p.caja}` : `Transferencia ${BANCO[p.medio] ?? p.medio}`}</span>
      <strong>{formatMoneda(p.importe)}</strong>
      {p.medio !== "caja" && <SoloLectura><button disabled={ocupado} className={boton} onClick={() => correr(() => quitarPagoTrabajo(t.idTrabajo, p.idPago), false)}>Quitar</button></SoloLectura>}
    </div>) : <p className="text-sm text-ink-secondary">Sin pagos registrados.</p>}
    {t.pagos?.some(p => p.medio === "caja") && <p className="text-xs text-ink-secondary">Un pago en efectivo se anula desde la caja, así se repone el saldo.</p>}

    {falta > 0 && <SoloLectura><div className="flex flex-wrap gap-2">
      <button className={boton} onClick={() => setModo(modo === "efectivo" ? "" : "efectivo")}>Pagar en efectivo</button>
      <button className={boton} onClick={() => setModo(modo === "transferencia" ? "" : "transferencia")}>Pagado por transferencia</button>
      <span className="self-center text-sm">Falta pagar {formatMoneda(falta)}</span>
    </div></SoloLectura>}

    {modo === "efectivo" && <div className="space-y-2 rounded border border-border p-3">
      <div className="grid gap-2 md:grid-cols-4">
        <label className="text-sm">Caja<select className={`${input} block w-full`} value={datos.caja} onChange={e => poner({ caja: e.target.value as PagoCajaInput["caja"] })}>{CAJAS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}</select></label>
        <label className="text-sm">Fecha<input type="date" className={`${input} block w-full`} value={datos.fecha} onChange={e => poner({ fecha: e.target.value })} /></label>
        <label className="text-sm">Importe<MoneyInput className={`${input} block w-full`} moneda="Pesos" value={datos.importe} onChange={v => poner({ importe: v })} /></label>
        <label className="text-sm">Cuenta<select className={`${input} block w-full`} value={datos.cuenta} onChange={e => poner({ cuenta: e.target.value as "A" | "B" })}><option value="A">A</option><option value="B">B</option></select></label>
        <label className="text-sm">Rubro<select className={`${input} block w-full`} value={datos.idRubro} onChange={e => poner({ idRubro: Number(e.target.value) })}><option value={0}>Elegir</option>{catalogos.data?.rubros.map(x => <option key={x.idRubro} value={x.idRubro}>{x.rubro}</option>)}</select></label>
        <label className="text-sm">Centro de costos<select className={`${input} block w-full`} value={datos.idCentroCostos} onChange={e => poner({ idCentroCostos: Number(e.target.value) })}><option value={0}>Elegir</option>{catalogos.data?.centrosCosto.map(x => <option key={x.idCentroCosto} value={x.idCentroCosto}>{x.centroCosto}</option>)}</select></label>
        <label className="text-sm">Campaña<select className={`${input} block w-full`} value={datos.idCampania ?? 0} onChange={e => poner({ idCampania: Number(e.target.value) || null })}><option value={0}>Sin asignar</option>{catalogos.data?.campañas.map(x => <option key={x.idCampania} value={x.idCampania}>{x.campania}</option>)}</select></label>
      </div>
      {!vista ? <button className={boton} disabled={ocupado || !datos.idRubro || !datos.idCentroCostos || !(datos.importe > 0)} onClick={previsualizar}>Ver cómo queda la caja</button> : <div className="space-y-2 text-sm">
        {vista.efectosPrevistos.map(e => <p key={e.caja}>Caja {NOMBRE_CAJA[e.caja] ?? e.caja}: sale {formatMoneda(-Number(e.importe))}, queda {formatMoneda(Number(e.saldoResultante))}.</p>)}
        {vista.advertencias.includes("SALDO_NEGATIVO") && <p className="text-amber-800">La caja queda en negativo.</p>}
        {vista.advertencias.includes("PERIODO_ARQUEADO") && <p className="text-amber-800">La fecha cae en un período con arqueo: el arqueo queda para rehacer.</p>}
        <button className={boton} disabled={ocupado} onClick={() => correr(() => pagarTrabajoCaja(t.idTrabajo, { ...datos, previewVersion: vista.previewVersion, advertenciasAceptadas: vista.advertencias }))}>Confirmar pago</button>
      </div>}
    </div>}

    {modo === "transferencia" && <div className="space-y-2 rounded border border-border p-3 text-sm">
      {transfer.isLoading && <p>Buscando transferencias…</p>}
      {transfer.data && !transfer.data.length && <p>No hay transferencias del banco a nombre de {t.trabajador} desde 15 días antes del trabajo. Si se pagó por transferencia y todavía no está, aparece al cargar el extracto.</p>}
      {transfer.data?.map(m => <div key={`${m.medio}-${m.id}`} className="flex flex-wrap items-center gap-3">
        <span>{formatFecha(m.fecha)} · {BANCO[m.medio] ?? m.medio} · {m.detalle}</span><strong>{formatMoneda(m.importe)}</strong>
        <button className={boton} disabled={ocupado} onClick={() => correr(() => pagarTrabajoTransferencia(t.idTrabajo, m.medio, m.id))}>Es este pago</button>
      </div>)}
    </div>}
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
  </div>;
}
