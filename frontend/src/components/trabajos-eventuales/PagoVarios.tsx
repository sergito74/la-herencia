"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { fetchFiltrosCompras } from "@/services/comprasApi";
import { fetchSocios } from "@/services/cuentasSociosApi";
import { formatFecha, formatMoneda } from "@/lib/format";
import { pagarVariosCaja, pagarVariosSocio, pagarVariosTransferencia, previsualizarPagoVarios, transferenciasVarios,
  type PagoCajaInput, type PagoSocioInput, type PreviewPagoTrabajo, type Trabajo } from "@/services/trabajosEventualesApi";

const input = "rounded border border-border bg-white px-2 py-1.5 text-sm";
const boton = "rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken disabled:opacity-50";
const CAJAS = [["giamigli-sa", "Giamigli SA"], ["campo-chica", "Caja chica"], ["condominio-lsc", "Condominio LSC"]] as const;
const NOMBRE_CAJA: Record<string, string> = Object.fromEntries(CAJAS);
const BANCO: Record<string, string> = { galicia: "Galicia", bna: "Banco Nación" };
const MODOS = [["socio", "Lo pagó un socio"], ["banco", "Transferencia de Giamigli"], ["efectivo", "Efectivo de una caja"]] as const;
const hoy = () => new Date().toLocaleDateString("sv-SE");

/** 18/11/2026: un solo pago para varios trabajos del mismo trabajador. Queda un único egreso (asiento del socio,
 * débito del banco de Giamigli o salida de caja) vinculado a todos; se reparte del trabajo más viejo al más nuevo. */
export function PagoVarios({ trabajos, onListo, cancelar }: { trabajos: Trabajo[]; onListo: () => void; cancelar: () => void }) {
  const ids = trabajos.map(t => t.idTrabajo);
  const faltaDe = (t: Trabajo) => Math.max(0, t.total - (t.pagado ?? 0));
  const falta = Math.round(trabajos.reduce((s, t) => s + faltaDe(t), 0) * 100) / 100;
  const [modo, setModo] = useState<(typeof MODOS)[number][0]>("socio");
  const [socio, setSocio] = useState<PagoSocioInput>({ idSocio: 0, fecha: hoy(), importe: falta, medio: "" });
  const [datos, setDatos] = useState<PagoCajaInput>({ caja: "giamigli-sa", fecha: hoy(), importe: falta, cuenta: "B", idRubro: 0, idCentroCostos: 0, idCampania: null });
  const [vista, setVista] = useState<PreviewPagoTrabajo | null>(null);
  const [error, setError] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const socios = useQuery({ queryKey: ["cuentas-socios"], queryFn: fetchSocios, enabled: modo === "socio" });
  const catalogos = useQuery({ queryKey: ["compras-filtros"], queryFn: fetchFiltrosCompras, enabled: modo === "efectivo" });
  const banco = useQuery({ queryKey: ["trabajos-transferencias", ids], queryFn: () => transferenciasVarios(ids), enabled: modo === "banco" });
  const poner = (c: Partial<PagoCajaInput>) => { setDatos(d => ({ ...d, ...c })); setVista(null); };

  async function correr(fn: () => Promise<unknown>, terminar = true) {
    setOcupado(true); setError("");
    try { await fn(); if (terminar) onListo(); }
    catch (e) { setError(e instanceof Error ? e.message : "No se pudo registrar el pago"); }
    finally { setOcupado(false); }
  }

  return <section className="space-y-3 rounded-lg border border-border bg-surface p-4 text-sm">
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h2 className="text-base font-semibold">
        Pagar {trabajos.length === 1 ? "1 trabajo" : `${trabajos.length} trabajos`} de {trabajos[0].trabajador} · falta {formatMoneda(falta)}
      </h2>
      <button className={boton} onClick={cancelar}>Cancelar</button>
    </div>
    <p className="text-ink-secondary">{trabajos.map(t => `${formatFecha(t.fecha)} ${t.descripcion} (${formatMoneda(faltaDe(t))})`).join(" · ")}</p>
    <div className="flex flex-wrap gap-2">
      {MODOS.map(([m, n]) => <button key={m} className={`${boton} ${modo === m ? "bg-surface-sunken font-medium" : ""}`}
        onClick={() => { setModo(m); setError(""); }}>{n}</button>)}
    </div>

    {modo === "socio" && <div className="space-y-2">
      <p className="text-ink-secondary">Un solo pago desde la cuenta personal del socio: queda a favor del socio en su cuenta y vinculado a todos estos trabajos.</p>
      <div className="grid gap-2 md:grid-cols-4">
        <label>Socio<select className={`${input} block w-full`} value={socio.idSocio} onChange={e => { const id = Number(e.target.value); setSocio(s => ({ ...s, idSocio: id, medio: socios.data?.socios.find(x => x.idSocio === id)?.medios?.[0] ?? "" })); }}><option value={0}>Elegir</option>{socios.data?.socios.map(x => <option key={x.idSocio} value={x.idSocio}>{x.nombre}</option>)}</select></label>
        <label>Fecha<input type="date" className={`${input} block w-full`} value={socio.fecha} onChange={e => setSocio(s => ({ ...s, fecha: e.target.value }))} /></label>
        <label>Importe<MoneyInput className={`${input} block w-full`} moneda="Pesos" value={socio.importe} onChange={v => setSocio(s => ({ ...s, importe: v }))} /></label>
        <label>Desde<select className={`${input} block w-full`} value={socio.medio} onChange={e => setSocio(s => ({ ...s, medio: e.target.value }))}>{!socio.idSocio && <option value="">Elegí el socio</option>}{socios.data?.socios.find(x => x.idSocio === socio.idSocio)?.medios?.map(m => <option key={m}>{m}</option>)}</select></label>
      </div>
      <button className={boton} disabled={ocupado || !socio.idSocio || !socio.medio || !(socio.importe > 0)} onClick={() => correr(() => pagarVariosSocio(ids, socio))}>Registrar el pago</button>
    </div>}

    {modo === "banco" && <div className="space-y-2">
      <p className="text-ink-secondary">Transferencias de Giamigli al trabajador ya cargadas del extracto, sin vincular. Elegí la que corresponde.</p>
      {banco.isLoading ? <p>Buscando transferencias…</p> : !banco.data?.length ? <p>No hay transferencias al trabajador sin vincular. Aparecen cuando se carga el extracto del banco.</p> :
        banco.data.map(m => <div key={`${m.medio}-${m.id}`} className="flex flex-wrap items-center gap-3">
          <span>{formatFecha(m.fecha)} · {BANCO[m.medio] ?? m.medio}{m.detalle ? ` · ${m.detalle}` : ""}</span><strong>{formatMoneda(m.importe)}</strong>
          <button className={boton} disabled={ocupado} onClick={() => correr(() => pagarVariosTransferencia(ids, m.medio, m.id))}>Vincular este pago</button>
        </div>)}
    </div>}

    {modo === "efectivo" && <div className="space-y-2">
      <div className="grid gap-2 md:grid-cols-4">
        <label>Caja<select className={`${input} block w-full`} value={datos.caja} onChange={e => poner({ caja: e.target.value as PagoCajaInput["caja"] })}>{CAJAS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}</select></label>
        <label>Fecha<input type="date" className={`${input} block w-full`} value={datos.fecha} onChange={e => poner({ fecha: e.target.value })} /></label>
        <label>Importe<MoneyInput className={`${input} block w-full`} moneda="Pesos" value={datos.importe} onChange={v => poner({ importe: v })} /></label>
        <label>Cuenta<select className={`${input} block w-full`} value={datos.cuenta} onChange={e => poner({ cuenta: e.target.value as "A" | "B" })}><option value="A">A</option><option value="B">B</option></select></label>
        <label>Rubro<select className={`${input} block w-full`} value={datos.idRubro} onChange={e => poner({ idRubro: Number(e.target.value) })}><option value={0}>Elegir</option>{catalogos.data?.rubros.map(x => <option key={x.idRubro} value={x.idRubro}>{x.rubro}</option>)}</select></label>
        <label>Centro de costos<select className={`${input} block w-full`} value={datos.idCentroCostos} onChange={e => poner({ idCentroCostos: Number(e.target.value) })}><option value={0}>Elegir</option>{catalogos.data?.centrosCosto.map(x => <option key={x.idCentroCosto} value={x.idCentroCosto}>{x.centroCosto}</option>)}</select></label>
        <label>Campaña<select className={`${input} block w-full`} value={datos.idCampania ?? 0} onChange={e => poner({ idCampania: Number(e.target.value) || null })}><option value={0}>Sin asignar</option>{catalogos.data?.campañas.map(x => <option key={x.idCampania} value={x.idCampania}>{x.campania}</option>)}</select></label>
      </div>
      {!vista ? <button className={boton} disabled={ocupado || !datos.idRubro || !datos.idCentroCostos || !(datos.importe > 0)}
          onClick={() => correr(async () => setVista(await previsualizarPagoVarios(ids, datos)), false)}>Ver cómo queda la caja</button>
        : <div className="space-y-2">
          {vista.efectosPrevistos.map(e => <p key={e.caja}>Caja {NOMBRE_CAJA[e.caja] ?? e.caja}: sale {formatMoneda(-Number(e.importe))}, queda {formatMoneda(Number(e.saldoResultante))}.</p>)}
          {vista.advertencias.includes("SALDO_NEGATIVO") && <p className="text-status-warning">La caja queda en negativo.</p>}
          {vista.advertencias.includes("PERIODO_ARQUEADO") && <p className="text-status-warning">La fecha cae en un período con arqueo: el arqueo queda para rehacer.</p>}
          <button className={boton} disabled={ocupado} onClick={() => correr(() => pagarVariosCaja(ids, { ...datos, previewVersion: vista.previewVersion, advertenciasAceptadas: vista.advertencias }))}>Confirmar pago</button>
        </div>}
    </div>}
    {error && <p role="alert" className="text-status-danger">{error}</p>}
  </section>;
}
