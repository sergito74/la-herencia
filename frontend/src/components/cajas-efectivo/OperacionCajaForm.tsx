"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { AvisoCuentaContacto } from "@/components/ui/AvisoCuentaContacto";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { fetchDocumentosPendientes } from "@/services/aplicacionesPagoApi";
import { fetchFiltrosCompras } from "@/services/comprasApi";
import { fetchSocios } from "@/services/cuentasSociosApi";
import { fetchMovimientos } from "@/services/tesoreriaApi";
import { fetchRemuneraciones } from "@/services/remuneracionesApi";
import { apiGet } from "@/services/apiClient";
import { formatFecha, formatMoneda } from "@/lib/format";
import {
  TIPOS_CAJA, monedaCaja, crearOperacionCaja, previsualizarCaja,
  type CajaSlug, type ConfirmacionCaja, type OperacionCajaInput, type PreviewCaja, type TipoOperacionCaja,
} from "@/services/cajasEfectivoApi";

export const nombresCaja: Record<CajaSlug, string> = { "giamigli-dolares": "Giamigli US$", "giamigli-sa": "Giamigli SA", "campo-chica": "Caja chica", "condominio-lsc": "Condominio LSC" };
export const hoyCaja = () => new Intl.DateTimeFormat("sv-SE", { timeZone: "America/Argentina/Buenos_Aires" }).format(new Date());
const input = "w-full rounded border border-border bg-surface px-3 py-2";
const button = "rounded border border-border px-3 py-2 disabled:opacity-50";

export function OperacionCajaForm({ caja, initial, onSaved, onPrepared }: {
  caja: CajaSlug;
  initial?: Partial<Omit<OperacionCajaInput, "cuenta">> & { cuenta?: string; razonSocial?: string };
  onSaved?: (id: number) => void;
  onPrepared?: (body: ConfirmacionCaja) => void;
}) {
  const moneda = monedaCaja(caja);
  const usd = moneda === "Dolares";
  const queryClient = useQueryClient();
  const [tipo, setTipo] = useState<TipoOperacionCaja>(initial?.tipo ?? (usd ? (Number(initial?.importe ?? 0) < 0 ? "egreso_dolares" : "ingreso_dolares") : (initial?.importe && Number(initial.importe) > 0 ? "aporte" : "pago")));
  const [fecha, setFecha] = useState(initial?.fecha ?? hoyCaja());
  const [importe, setImporte] = useState(Math.abs(Number(initial?.importe ?? 0)));
  const [concepto, setConcepto] = useState(initial?.concepto ?? "");
  const [cuenta, setCuenta] = useState<"A" | "B">(initial?.cuenta === "B" ? "B" : "A");
  const [contacto, setContacto] = useState<number | null>(initial?.idContacto ?? null);
  const [razonSocial, setRazonSocial] = useState<string | null>(initial?.razonSocial ?? null);
  const [socio, setSocio] = useState(initial?.compraParticular?.idSocio ?? initial?.idSocio ?? 0);
  const [destino, setDestino] = useState<CajaSlug>(initial?.cajaDestino ?? (caja === "giamigli-sa" ? "campo-chica" : "giamigli-sa"));
  const [contraparte, setContraparte] = useState(!!initial?.cajaContraparte);
  const [motivo, setMotivo] = useState(initial?.motivoRelacionGiamigli ?? "");
  const [seleccion, setSeleccion] = useState<Record<string, number>>(Object.fromEntries((initial?.aplicaciones ?? []).map(a => [`${a.tipoDocumento}:${a.idDocumento}`, Number(a.importeAplicado)])));
  const [particular, setParticular] = useState(!!initial?.compraParticular);
  const [compra, setCompra] = useState(initial?.compraParticular?.idCompra ?? 0);
  const [asiento, setAsiento] = useState(initial?.compraParticular?.idAsientoParticular ?? 0);
  const [asientoNuevo, setAsientoNuevo] = useState(initial?.compraParticular?.confirmarAsientoNuevo ?? false);
  const [medio, setMedio] = useState<"bna" | "galicia" | "mercado-libre">(initial?.banco?.medio ?? initial?.bancoPendiente ?? "bna");
  const [vincularExtracto, setVincularExtracto] = useState(!!initial?.banco);
  const [banco, setBanco] = useState(initial?.banco?.idMovimiento ?? 0);
  const [intermediario, setIntermediario] = useState(initial?.intermediario ?? "");
  const [evidencia, setEvidencia] = useState(initial?.evidencia ?? "");
  const [transaccion, setTransaccion] = useState(initial?.numeroTransaccion ?? "");
  const [salario, setSalario] = useState(initial?.idSalario ?? 0);
  const [repartos, setRepartos] = useState(initial?.repartos?.map(r => ({ ...r, idDestino: r.idDestino ?? 0, idCampania: r.idCampania ?? 0, importePesos: Number(r.importePesos) })) ?? [{ idRubro: 0, idCentroCostos: 0, idDestino: 0, idCampania: 0, importePesos: importe }]);
  const [preview, setPreview] = useState<PreviewCaja | null>(null);
  const [aceptadas, setAceptadas] = useState<string[]>([]);
  const [mensaje, setMensaje] = useState("");
  const clave = useRef(crypto.randomUUID());
  const esContacto = tipo === "pago" || tipo === "cobro";
  const esCanje = tipo === "canje_socio";
  const esSocio = ["aporte", "retiro_a_cuenta", "retiro_ganancias", "canje_socio"].includes(tipo);
  const esBanco = ["extraccion_banco", "deposito_banco", "retorno_sueldo_opcion_a", "canje_socio"].includes(tipo);
  const usaExtracto = esBanco && (!esCanje || vincularExtracto);
  const docs = useQuery({ queryKey: ["caja-documentos", contacto, tipo], queryFn: () => fetchDocumentosPendientes(contacto!, tipo === "pago" ? "compra" : "venta"), enabled: esContacto && !!contacto });
  const socios = useQuery({ queryKey: ["cuentas-socios"], queryFn: fetchSocios, enabled: esSocio || particular });
  const catalogos = useQuery({ queryKey: ["compras-filtros"], queryFn: fetchFiltrosCompras, enabled: tipo === "gasto_sin_comprobante" });
  const compraElegida = docs.data?.find(d => d.tipoDocumento === "CompraDeuda" && d.idDocumento === compra);
  const importeParticular = compraElegida?.importePersonal ?? 0;
  const asientos = useQuery({ queryKey: ["caja-asientos-particulares", contacto, fecha, importeParticular],
    queryFn: () => apiGet<{ items: { id: number; caja: string; fecha: string }[] }>("/api/cajas-efectivo/particulares/asientos", { idContacto: contacto!, fecha, importe: importeParticular.toFixed(2) }), enabled: particular && !!contacto && importeParticular > 0 });
  const movimientos = useQuery({ queryKey: ["caja-banco-candidatos", medio, fecha], queryFn: () => fetchMovimientos(medio, { fechaDesde: fecha, fechaHasta: fecha, page: 1, pageSize: 200 }), enabled: usaExtracto });
  const salarios = useQuery({ queryKey: ["caja-sueldos"], queryFn: () => fetchRemuneraciones({ empleado: "Sergio", pageSize: 200 }), enabled: tipo === "retorno_sueldo_opcion_a" });
  const bankOptions = (movimientos.data?.items ?? []).map(m => {
    const id = "idMovimientoBNA" in m ? m.idMovimientoBNA : m.idMovimiento;
    const value = "debitos" in m ? (m.creditos ?? 0) - (m.debitos ?? 0) : m.importe ?? 0;
    const label = "concepto" in m ? m.concepto : m.descripcion;
    return { id, value, label, estado: m.estadoConciliacion };
  }).filter(m => !esCanje || (m.value < 0 && (!m.estado || ["sin_conciliar", "ya_reconocido"].includes(m.estado))));
  const op = useMemo<OperacionCajaInput>(() => {
    const aplicaciones = particular ? [{ tipoDocumento: "CompraDeuda", idDocumento: compra, importeAplicado: importe.toFixed(2) }] : Object.entries(seleccion).filter(([, v]) => v > 0).map(([key, value]) => {
      const [tipoDocumento, id] = key.split(":"); return { tipoDocumento, idDocumento: Number(id), importeAplicado: value.toFixed(2) };
    });
    return { tipo, caja, fecha, importe: importe.toFixed(2), concepto, cuenta,
      ...(esContacto ? { idContacto: contacto ?? 0, aplicaciones } : {}),
      ...(esSocio ? { idSocio: socio } : {}),
      ...(tipo === "traspaso_cajas" ? { cajaDestino: destino } : {}),
      ...((tipo === "aporte" || tipo === "retiro_a_cuenta") && socio === 3 && contraparte ? { cajaContraparte: "condominio-lsc" as CajaSlug } : {}),
      ...(caja === "condominio-lsc" || (socio === 3 && contraparte && !esCanje) ? { motivoRelacionGiamigli: motivo } : {}),
      ...(esCanje && !vincularExtracto ? { bancoPendiente: medio, evidencia: evidencia || undefined } : {}),
      ...(esCanje && transaccion.trim() ? { numeroTransaccion: transaccion.trim() } : {}),
      ...(usaExtracto ? { banco: { medio, idMovimiento: banco }, intermediario: intermediario || undefined, evidencia: evidencia || undefined } : {}),
      ...(tipo === "retorno_sueldo_opcion_a" ? { idSalario: salario } : {}),
      ...(tipo === "pago" && particular ? { compraParticular: { idCompra: compra, idSocio: socio, idAsientoParticular: asiento || undefined, confirmarAsientoNuevo: asientoNuevo } } : {}),
      ...(tipo === "gasto_sin_comprobante" ? { repartos: repartos.map(r => ({ ...r, idDestino: r.idDestino || undefined, idCampania: r.idCampania || undefined, importePesos: r.importePesos.toFixed(2) })) } : {}),
    };
  }, [tipo, caja, fecha, importe, concepto, cuenta, esContacto, contacto, seleccion, esSocio, esCanje, socio, destino, contraparte, motivo, usaExtracto, vincularExtracto, medio, banco, transaccion, intermediario, evidencia, salario, particular, compra, asiento, asientoNuevo, repartos]);
  const serializado = JSON.stringify(op);
  useEffect(() => { setPreview(null); setAceptadas([]); clave.current = crypto.randomUUID(); }, [serializado]);
  const revisar = useMutation({ mutationFn: () => previsualizarCaja(op), onSuccess: p => { setPreview(p); setMensaje(""); } });
  const guardar = useMutation({ mutationFn: () => crearOperacionCaja({ operacion: op, previewVersion: preview!.previewVersion, advertenciasAceptadas: aceptadas }, clave.current), onSuccess: async result => {
    setPreview(null); clave.current = crypto.randomUUID(); setMensaje(esCanje ? (op.bancoPendiente ? "Canje registrado. La transferencia queda pendiente de conciliar con el resumen bancario." : "Efectivo y transferencia registrados. El saldo del socio no cambió.") : `Operación ${result.idOperacion} registrada.`);
    await queryClient.invalidateQueries({ predicate: q => q.queryKey[0] !== "auth" }); onSaved?.(result.idOperacion);
  } });
  const error = revisar.error ?? guardar.error;
  const valuation = preview?.contexto.valuacion ?? preview?.contexto.particular?.valuacion;
  const activas = [
    { q: docs, activa: esContacto && !!contacto }, { q: socios, activa: esSocio || particular },
    { q: catalogos, activa: tipo === "gasto_sin_comprobante" }, { q: asientos, activa: particular && !!contacto && importeParticular > 0 },
    { q: movimientos, activa: usaExtracto }, { q: salarios, activa: tipo === "retorno_sueldo_opcion_a" },
  ];
  const queryError = activas.some(({ q, activa }) => activa && q.isError);
  function setAplicado(key: string, value: number) {
    const next = { ...seleccion, [key]: value }; setSeleccion(next); setImporte(Object.values(next).reduce((a, b) => a + b, 0));
  }
  return <form className="space-y-4" onSubmit={e => { e.preventDefault(); revisar.mutate(); }}>
    {onPrepared && <h3 className="font-semibold">Clasificar fila de planilla — {nombresCaja[caja]}</h3>}
    {usd && <p>Importes y saldo en US$ billete. Los aportes y retiros a cuenta del socio se registran íntegramente en dólares, sin kg INMAG.</p>}
    <div className="grid gap-3 md:grid-cols-3">
      <label className="md:col-span-3">Operación<select className={input} value={tipo} onChange={e => { setTipo(e.target.value as TipoOperacionCaja); setSeleccion({}); setParticular(false); setCompra(0); setContraparte(false); if (e.target.value === "canje_socio" && !concepto.trim()) setConcepto("Efectivo contra transferencia al socio"); }}>
        {Object.entries(TIPOS_CAJA).filter(([t]) => caja === "condominio-lsc" ? t === "pago" : usd ? ["ingreso_dolares", "egreso_dolares", "aporte", "retiro_a_cuenta", "retiro_ganancias"].includes(t) : !["ingreso_dolares", "egreso_dolares"].includes(t)).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select></label>
      <label>Fecha<input className={input} type="date" required value={fecha} onChange={e => setFecha(e.target.value)} /></label>
      <label>Cuenta<select className={input} value={cuenta} onChange={e => setCuenta(e.target.value as "A" | "B")}><option>A</option><option>B</option></select></label>
      <label>Importe<MoneyInput className={input} moneda={moneda} value={importe} onChange={setImporte} /></label>
      <label className="md:col-span-3">Concepto<input className={input} required maxLength={255} value={concepto} onChange={e => setConcepto(e.target.value)} /></label>
    </div>
    {esContacto && <><ContactoSelect value={contacto} razonSocial={razonSocial} label={tipo === "pago" ? "Proveedor" : "Cliente / comprador"} onChange={(id, nombre) => { setContacto(id); setRazonSocial(nombre); setSeleccion({}); setCompra(0); }} /><AvisoCuentaContacto idContacto={contacto} />
      {tipo === "pago" && caja !== "condominio-lsc" && <label className="block"><input type="checkbox" checked={particular} onChange={e => { setParticular(e.target.checked); setSeleccion({}); }} /> Compra particular de un socio</label>}
      {!particular && docs.isFetching && <p>Buscando documentos…</p>}
      {!particular && contacto && docs.data?.length === 0 && <p>No hay documentos pendientes compatibles.</p>}
      {!particular && <div className="max-h-64 space-y-2 overflow-auto">{docs.data?.map(d => { const k = `${d.tipoDocumento}:${d.idDocumento}`; return <div key={k} className="flex flex-wrap items-center gap-3 rounded border border-border p-2">
        <label className="flex-1"><input type="checkbox" checked={!!seleccion[k]} onChange={e => setAplicado(k, e.target.checked ? d.saldoPendiente : 0)} /> {d.numeroDocumento || "Sin número"} · {formatFecha(d.fecha)} · pendiente {formatMoneda(d.saldoPendiente)}</label>
        {!!seleccion[k] && <MoneyInput className={input + " max-w-44"} value={seleccion[k]} moneda="Pesos" onChange={v => setAplicado(k, v)} />}
      </div>; })}</div>}
      {particular && <><label>Compra particular<select className={input} value={compra} onChange={e => { const id = Number(e.target.value); setCompra(id); const selected = docs.data?.find(d => d.idDocumento === id); if (selected) setImporte(selected.saldoPendiente); }}><option value={0}>Elegir compra</option>{docs.data?.filter(d => d.tipoDocumento === "CompraDeuda" && d.esParticular).map(d => <option value={d.idDocumento} key={d.idDocumento}>{d.numeroDocumento} · {formatFecha(d.fecha)} · pendiente {formatMoneda(d.saldoPendiente)}</option>)}</select></label>
        {!!asientos.data?.items.length && <label>Asiento particular existente<select className={input} value={asiento} onChange={e => setAsiento(Number(e.target.value))}><option value={0}>Elegir asiento o confirmar que es otro</option>{asientos.data.items.map(a => <option key={a.id} value={a.id}>{a.caja} · {formatFecha(a.fecha)}</option>)}</select></label>}
        <label className="block"><input type="checkbox" checked={asientoNuevo} onChange={e => setAsientoNuevo(e.target.checked)} /> Confirmo que debe crearse un asiento particular nuevo</label></>}
    </>}
    {(esSocio || particular) && <label>Socio<select className={input} value={socio} onChange={e => setSocio(Number(e.target.value))}><option value={0}>Elegir socio</option>{socios.data?.socios.map(s => <option key={s.idSocio} value={s.idSocio}>{s.nombre}</option>)}</select></label>}
    {esCanje && <p>El socio entrega efectivo a Giamigli y recibe el mismo importe por transferencia. Se registra todo junto y su saldo no cambia.</p>}
    {esSocio && socio === 3 && !usd && caja !== "condominio-lsc" && tipo !== "retiro_ganancias" && !esCanje && <label className="block"><input type="checkbox" checked={contraparte} onChange={e => setContraparte(e.target.checked)} /> Registrar también la salida / devolución en los movimientos vinculados del Condominio</label>}
    {(caja === "condominio-lsc" || (socio === 3 && contraparte && !esCanje)) && <label>Relación con Giamigli<input className={input} required maxLength={255} value={motivo} onChange={e => setMotivo(e.target.value)} /></label>}
    {tipo === "retiro_ganancias" && <p>Distribución de ganancias: no genera deuda ni crédito del socio.</p>}
    {tipo === "traspaso_cajas" && <label>Caja de destino<select className={input} value={destino} onChange={e => setDestino(e.target.value as CajaSlug)}>{(["giamigli-sa", "campo-chica"] as CajaSlug[]).filter(c => c !== caja).map(c => <option value={c} key={c}>{nombresCaja[c]}</option>)}</select></label>}
    {esBanco && <div className="grid gap-3 md:grid-cols-2"><label>Banco<select className={input} value={medio} onChange={e => { setMedio(e.target.value as typeof medio); setBanco(0); }}><option value="bna">Banco Nación</option><option value="galicia">Galicia</option><option value="mercado-libre">Mercado Pago</option></select></label>
      {esCanje && <label className="md:col-span-2"><input type="checkbox" checked={vincularExtracto} onChange={e => { setVincularExtracto(e.target.checked); setBanco(0); }} /> Vincular ahora con una transferencia del extracto</label>}
      {usaExtracto && <label>{esCanje ? "Transferencia al socio" : "Movimiento del extracto (fecha elegida)"}<select className={input} value={banco} onChange={e => { const id = Number(e.target.value); setBanco(id); const m = bankOptions.find(m => m.id === id); if (m) setImporte(Math.abs(m.value)); }}><option value={0}>{esCanje ? "Elegir transferencia" : "Elegir movimiento importado"}</option>{bankOptions.map(m => <option key={m.id} value={m.id}>{m.label} · {formatMoneda(esCanje ? Math.abs(m.value) : m.value)}{!esCanje && ` · ${m.estado}`}</option>)}</select></label>}
      {esCanje && <label>Número de transacción del banco (opcional)<input className={input} maxLength={60} value={transaccion} onChange={e => setTransaccion(e.target.value)} /><span className="block text-sm">Queda en el asiento de caja para ubicar la transferencia en el resumen.</span></label>}
      {esCanje && !usaExtracto && <p>Podés guardar sin el resumen bancario. La transferencia quedará pendiente de conciliación.</p>}
      {!esCanje && <label>Intermediario, si corresponde<input className={input} maxLength={255} value={intermediario} onChange={e => setIntermediario(e.target.value)} /></label>}<label>{esCanje ? "Referencia de la transferencia (opcional)" : "Evidencia / referencia"}<input className={input} maxLength={255} value={evidencia} onChange={e => setEvidencia(e.target.value)} required={tipo === "retorno_sueldo_opcion_a"} /></label>
      {esCanje && usaExtracto && !movimientos.isFetching && !movimientos.isError && bankOptions.length === 0 && <p>No hay transferencias disponibles para esa fecha. Podés desmarcar «Vincular ahora» para guardar y conciliar cuando llegue el resumen.</p>}
      {usaExtracto && !!banco && <a className="underline" href={`/finanzas/tesoreria?medio=${medio}&highlight=${banco}`}>Ver extracto bancario</a>}
    </div>}
    {tipo === "retorno_sueldo_opcion_a" && <label>Liquidación de Sergio empleado<select className={input} value={salario} onChange={e => setSalario(Number(e.target.value))}><option value={0}>Elegir liquidación documentada</option>{salarios.data?.items.filter(s => s.idContacto === 375).map(s => <option key={s.idSalario} value={s.idSalario}>{s.periodoLiquidado} · {formatMoneda(s.importe ?? 0)}</option>)}</select><p>Se registra como no cobrado más traspaso; los pares históricos compensados conservan su tratamiento.</p></label>}
    {tipo === "gasto_sin_comprobante" && <div className="space-y-2"><p>Repartir el gasto. La suma debe coincidir con el importe.</p>{repartos.map((r, i) => {
      const update = (next: Partial<typeof r>) => setRepartos(prev => prev.map((x, k) => k === i ? { ...x, ...next } : x));
      return <div key={i} className="grid gap-2 rounded border border-border p-2 md:grid-cols-3">
        <label>Rubro<select className={input} value={r.idRubro} onChange={e => update({ idRubro: Number(e.target.value) })}><option value={0}>Elegir</option>{catalogos.data?.rubros.map(x => <option key={x.idRubro} value={x.idRubro}>{x.rubro}</option>)}</select></label>
        <label>Centro de costos<select className={input} value={r.idCentroCostos} onChange={e => update({ idCentroCostos: Number(e.target.value) })}><option value={0}>Elegir</option>{catalogos.data?.centrosCosto.map(x => <option key={x.idCentroCosto} value={x.idCentroCosto}>{x.centroCosto}</option>)}</select></label>
        <label>Destino<select className={input} value={r.idDestino} onChange={e => update({ idDestino: Number(e.target.value) })}><option value={0}>Sin asignar</option>{catalogos.data?.destinos.map(x => <option key={x.idDestino} value={x.idDestino}>{x.destino}</option>)}</select></label>
        <label>Campaña<select className={input} value={r.idCampania} onChange={e => update({ idCampania: Number(e.target.value) })}><option value={0}>Sin asignar</option>{catalogos.data?.campañas.map(x => <option key={x.idCampania} value={x.idCampania}>{x.campania}</option>)}</select></label>
        <label>Importe del reparto<MoneyInput className={input} moneda="Pesos" value={r.importePesos} onChange={v => update({ importePesos: v })} /></label>
        {repartos.length > 1 && <button className={button} type="button" onClick={() => setRepartos(prev => prev.filter((_, k) => k !== i))}>Quitar reparto</button>}
      </div>;
    })}<button type="button" className={button} onClick={() => setRepartos(prev => [...prev, { idRubro: 0, idCentroCostos: 0, idDestino: 0, idCampania: 0, importePesos: 0 }])}>Agregar reparto</button></div>}
    {queryError && <p role="alert" className="text-status-danger">No se pudo cargar uno de los listados. <button type="button" className="underline" onClick={() => activas.filter(({ activa, q }) => activa && q.isError).forEach(({ q }) => q.refetch())}>Reintentar conservando el borrador</button></p>}
    {error && <p role="alert" className="text-status-danger">{error.message}</p>}
    {mensaje && <p role="status" className="text-status-success">{mensaje}</p>}
    <button className={button} disabled={revisar.isPending || guardar.isPending || importe <= 0 || queryError || (particular && docs.isFetching) || (esCanje && (!socio || (usaExtracto && (!banco || movimientos.isFetching || !bankOptions.some(m => m.id === banco)))))}>{revisar.isPending ? "Revisando…" : "Revisar efectos antes de guardar"}</button>
    {preview && <div className="space-y-3 rounded border border-border p-3"><h4 className="font-semibold">Efectos antes de guardar</h4>{preview.efectosPrevistos.map(p => <p key={p.caja}>{nombresCaja[p.caja]}: {formatMoneda(Number(p.importe), monedaCaja(p.caja))} · saldo resultante {formatMoneda(Number(p.saldoResultante), monedaCaja(p.caja))}</p>)}
      {valuation && <p>Valuación: {formatMoneda(Number(valuation.importeUSD), "Dolares")} y {valuation.importeKgCarne} kg de novillo.</p>}
      {preview.contexto.particular && <p>Parte particular documentada: {formatMoneda(Number(preview.contexto.particular.importe))}. Se refleja el gasto del socio una sola vez; el pago al proveedor puede ser parcial.</p>}
      {esCanje && <><p>Transferencia al socio: {formatMoneda(-Number(op.importe))} desde el banco de Giamigli.</p>{op.numeroTransaccion && <p>Transacción bancaria N° {op.numeroTransaccion}.</p>}{op.bancoPendiente && <p>Transferencia pendiente de conciliar cuando cargues el resumen bancario.</p>}<p>Saldo del socio: sin cambios. La entrega de efectivo y la transferencia se compensan.</p></>}
      {!esCanje && !!preview.contexto.banco?.cuentasExcluidas.length && <p>El movimiento bancario dejará de figurar como pago/cobro del contacto; quedará vinculado a esta caja.</p>}
      {preview.advertencias.map(w => <label key={w} className="block"><input type="checkbox" checked={aceptadas.includes(w)} onChange={e => setAceptadas(prev => e.target.checked ? [...prev, w] : prev.filter(x => x !== w))} /> {w === "SALDO_NEGATIVO" ? "Confirmo que la caja puede quedar en negativo." : "Confirmo que afecta un período arqueado y que sus arqueos deberán revisarse."}</label>)}
      <button type="button" className={button} disabled={guardar.isPending || preview.advertencias.some(w => !aceptadas.includes(w))} onClick={() => onPrepared ? onPrepared({ operacion: op, previewVersion: preview.previewVersion, advertenciasAceptadas: aceptadas }) : guardar.mutate()}>{guardar.isPending ? "Guardando…" : onPrepared ? "Usar para esta fila" : "Confirmar operación"}</button>
    </div>}
  </form>;
}
