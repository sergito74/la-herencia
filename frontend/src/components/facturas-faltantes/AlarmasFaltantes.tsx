"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { formatFecha, formatMoneda } from "@/lib/format";
import {
  anularMarca, crearMarca, descartarAlarma, fetchAlarmas, fetchMarcas, type Alarma, type MedioPago, type TipoAlarma,
} from "@/services/facturasFaltantesApi";

const TIPOS: Record<TipoAlarma, string> = {
  "pago-sin-factura": "Pago sin factura",
  "saldo-a-favor": "Saldo a favor antiguo",
  "retencion-sin-factura": "Retención sin factura",
  "remito-sin-factura": "Remito sin facturar",
};
const MEDIOS: Record<string, string> = { galicia: "Galicia", bna: "Banco Nación", efectivo: "Efectivo" };

function FilaAlarma({ a }: { a: Alarma }) {
  const cache = useQueryClient();
  const [motivo, setMotivo] = useState("");
  const refrescar = () => cache.invalidateQueries({ queryKey: ["facturas-faltantes"] });
  const descartar = useMutation({ mutationFn: () => descartarAlarma(a.clave, motivo), onSuccess: refrescar });
  const marcar = useMutation({
    mutationFn: () => crearMarca({ idContacto: a.idContacto, origenPago: a.origen!.medio as MedioPago, idPago: a.origen!.id, importeAprox: a.importe ?? undefined }),
    onSuccess: refrescar,
  });
  const error = descartar.error ?? marcar.error;
  return <tr className="border-t border-border align-top">
    <td className="p-2">{formatFecha(a.fecha)}</td>
    <td className="p-2"><Link className="underline" href={`/finanzas/cuentas-corrientes?idContacto=${a.idContacto}`}>{a.proveedor}</Link></td>
    <td className="p-2">{TIPOS[a.tipo]}<span className="block text-xs text-ink-secondary">{a.detalle}{a.origen && MEDIOS[a.origen.medio] ? ` · ${MEDIOS[a.origen.medio]}` : ""}</span></td>
    <td className="p-2 text-right">{a.importe != null ? formatMoneda(a.importe) : "—"}</td>
    <td className="p-2"><SoloLectura><div className="space-y-1">
      {a.tipo === "pago-sin-factura" && <button className="block underline disabled:opacity-50" disabled={marcar.isPending} onClick={() => marcar.mutate()}>Marcar como «a cuenta, falta factura»</button>}
      <input className="w-48 rounded border border-border p-1" maxLength={255} placeholder="Motivo para descartar" value={motivo} onChange={e => setMotivo(e.target.value)} />
      <button className="block underline disabled:opacity-50" disabled={!motivo.trim() || descartar.isPending} onClick={() => descartar.mutate()}>Descartar</button>
      {error && <p role="alert" className="text-status-danger">{error.message}</p>}
    </div></SoloLectura></td>
  </tr>;
}

function Marcas() {
  const cache = useQueryClient();
  const q = useQuery({ queryKey: ["facturas-faltantes", "marcas"], queryFn: () => fetchMarcas("abierta") });
  const anular = useMutation({ mutationFn: (id: number) => anularMarca(id, "Anulada desde el tablero"), onSuccess: () => cache.invalidateQueries({ queryKey: ["facturas-faltantes"] }) });
  if (q.isError) return <p role="alert">No se pudieron cargar los pagos marcados. <button className="underline" onClick={() => q.refetch()}>Reintentar</button></p>;
  if (!q.data?.length) return null;
  return <section className="space-y-1"><h3 className="font-semibold">Pagos a cuenta, falta factura ({q.data.length})</h3>
    <ul className="text-sm">{q.data.map(m => <li key={m.idMarca}>{m.proveedor} · {MEDIOS[m.origenPago]}{m.importeAprox != null && ` · ${formatMoneda(m.importeAprox)}`} · marcado el {formatFecha(m.fechaAlta)}
      <SoloLectura><span> · <button className="underline" onClick={() => anular.mutate(m.idMarca)}>Quitar marca</button></span></SoloLectura></li>)}</ul>
    <p className="text-xs text-ink-secondary">La marca se cierra sola cuando se carga una factura del proveedor de importe compatible.</p>
  </section>;
}

export function AlarmasFaltantes() {
  const [tipo, setTipo] = useState<TipoAlarma | "">("");
  const [page, setPage] = useState(1);
  const q = useQuery({ queryKey: ["facturas-faltantes", "alarmas", tipo, page], queryFn: () => fetchAlarmas(tipo, page) });
  return <section className="space-y-3">
    <Marcas />
    <label className="block text-sm">Tipo<select className="ml-2 rounded border border-border p-1" value={tipo} onChange={e => { setTipo(e.target.value as TipoAlarma | ""); setPage(1); }}>
      <option value="">Todas</option>{Object.entries(TIPOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
    {q.isLoading && <p>Buscando alarmas…</p>}
    {q.isError && <p role="alert">No se pudieron cargar las alarmas. <button className="underline" onClick={() => q.refetch()}>Reintentar</button></p>}
    {q.data && (q.data.total === 0 ? <p>No hay alarmas para verificar.</p> : <>
      <p className="text-sm">{q.data.total} alarmas para verificar con el comprobante; no son errores confirmados.</p>
      <table className="w-full text-sm"><thead><tr className="text-left text-ink-secondary"><th className="p-2">Fecha</th><th className="p-2">Proveedor</th>
        <th className="p-2">Señal</th><th className="p-2 text-right">Importe</th><th className="p-2" /></tr></thead>
        <tbody>{q.data.items.map(a => <FilaAlarma key={a.clave} a={a} />)}</tbody></table>
      <div className="flex gap-3 text-sm"><button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Anterior</button><span>Página {page}</span>
        <button disabled={page * q.data.pageSize >= q.data.total} onClick={() => setPage(p => p + 1)}>Siguiente</button></div>
    </>)}
  </section>;
}
