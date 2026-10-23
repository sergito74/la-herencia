"use client";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { detalleOperacionCaja, anularOperacionCaja } from "@/services/cajasEfectivoApi";
import { formatFecha, formatMoneda } from "@/lib/format";
import { nombresCaja, OperacionCajaForm } from "./OperacionCajaForm";
const efectos: Record<string, string> = { PagoEfectivo: "Pago/cobro en efectivo", Aplicacion: "Aplicación de comprobante", MovimientoSocio: "Cuenta de socio", AsientoParticular: "Asiento particular", TraspasoTesoreria: "Traspaso bancario", GastoCaja: "Gasto interno", AjusteNoCobrado: "Ajuste de sueldo no cobrado" };

export function DetalleOperacionCaja({ id, onClose }: { id: number; onClose: () => void }) {
  const cache = useQueryClient();
  const [motivo, setMotivo] = useState("");
  const [aceptadas, setAceptadas] = useState<string[]>([]);
  const [corregir, setCorregir] = useState(false);
  const detalle = useQuery({ queryKey: ["caja-operacion", id], queryFn: () => detalleOperacionCaja(id) });
  const anular = useMutation({ mutationFn: () => anularOperacionCaja(id, motivo, detalle.data!.version, detalle.data?.anulacion?.previewVersion, aceptadas), onSuccess: async () => { await cache.invalidateQueries({ predicate: q => q.queryKey[0] !== "auth" }); } });
  const d = detalle.data;
  useEffect(() => { setAceptadas([]); }, [d?.anulacion?.previewVersion]);
  function origen(tipo: string, ref: number) {
    if (tipo === "PagoEfectivo" || tipo === "AsientoParticular") return `/finanzas/tesoreria?medio=efectivo&highlight=${ref}`;
    if (tipo === "MovimientoSocio") return "/finanzas/cuentas-socios";
    return null;
  }
  return <section className="space-y-3 rounded border border-border bg-surface p-4" aria-label={`Detalle de operación ${id}`}>
    <div className="flex justify-between"><h3 className="font-semibold">Operación {id}</h3><button type="button" onClick={onClose}>Cerrar detalle</button></div>
    {detalle.isLoading && <p>Cargando detalle…</p>}
    {detalle.isError && <p role="alert">{detalle.error.message} <button onClick={() => detalle.refetch()}>Reintentar</button></p>}
    {d && <><p>{d.estado} · {d.operacion.concepto} · {formatFecha(d.operacion.fecha)} · {formatMoneda(Number(d.operacion.importe))}</p><p>Registró {d.usuario} · {d.fechaCarga}</p>
      {d.operacion.idContacto && <a className="underline" href={`/finanzas/cuentas-corrientes?idContacto=${d.operacion.idContacto}`}>Ver cuenta del contacto</a>}
      {d.operacion.banco && <a className="block underline" href={`/finanzas/tesoreria?medio=${d.operacion.banco.medio}&highlight=${d.operacion.banco.idMovimiento}`}>Ver movimiento bancario de origen</a>}
      <ul>{d.efectos.map(e => { const url = origen(e.tipo, e.idRegistro); return <li key={`${e.tipo}:${e.idRegistro}`}>{url ? <a className="underline" href={url}>{efectos[e.tipo] ?? e.tipo} {e.idRegistro}</a> : `${efectos[e.tipo] ?? e.tipo} ${e.idRegistro}`} · {e.propio ? "generado por esta operación" : "vínculo preexistente"}</li>; })}</ul>
      {d.estado === "Anulada" ? <div className="space-y-3"><p>Anuló {d.usuarioAnulacion} · {d.fechaAnulacion} · {d.motivoAnulacion}</p>
        <SoloLectura>{corregir ? <OperacionCajaForm caja={d.operacion.caja} initial={{ tipo: d.operacion.tipo, fecha: d.operacion.fecha, importe: d.operacion.importe, concepto: d.operacion.concepto, cuenta: d.operacion.cuenta, idSocio: d.operacion.idSocio, idContacto: d.operacion.idContacto }} onSaved={() => onClose()} />
          : <button className="rounded-sm bg-agro px-3 py-2 text-sm text-white" onClick={() => setCorregir(true)}>Corregir: cargar de nuevo con estos datos</button>}</SoloLectura></div> : <SoloLectura><div className="space-y-2"><label>Motivo de anulación<input className="ml-2 rounded border border-border p-2" maxLength={255} value={motivo} onChange={e => setMotivo(e.target.value)} /></label><p>La anulación conserva el historial y revierte juntos los efectos generados por esta operación. Para corregir: anulá y después usá «Corregir», que abre el formulario con los mismos datos.</p>
        {d.anulacion?.bloqueo && <p role="alert">{d.anulacion.bloqueo}</p>}
        {d.anulacion?.efectosPrevistos?.map(p => <p key={p.caja}>{nombresCaja[p.caja]}: saldo después de anular {formatMoneda(Number(p.saldoResultante))}</p>)}
        {d.anulacion?.advertencias?.map(w => <label className="block" key={w}><input type="checkbox" checked={aceptadas.includes(w)} onChange={e => setAceptadas(prev => e.target.checked ? [...prev, w] : prev.filter(x => x !== w))} /> {w === "SALDO_NEGATIVO" ? "Confirmo que la anulación deja saldo negativo." : "Confirmo que la anulación modifica un período arqueado."}</label>)}
        <button className="rounded border border-border p-2 text-status-danger disabled:opacity-50" disabled={!motivo.trim() || anular.isPending || !!d.anulacion?.bloqueo || d.anulacion?.advertencias?.some(w => !aceptadas.includes(w))} onClick={() => anular.mutate()}>{anular.isPending ? "Anulando…" : "Confirmar anulación"}</button></div></SoloLectura>}
    </>}
    {anular.isError && <p role="alert" className="text-status-danger">{anular.error.message}</p>}
  </section>;
}
