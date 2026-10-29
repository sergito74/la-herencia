"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { formatFecha, formatMoneda } from "@/lib/format";
import {
  descartarAlarma, fetchTablero, guardarPerfil, responderBaja, type EstadoPeriodo, type FilaTablero,
} from "@/services/facturasFaltantesApi";

const ESTADOS: Record<EstadoPeriodo, { texto: string; clase: string }> = {
  atrasada: { texto: "Atrasada — a verificar", clase: "text-status-danger" },
  baja: { texto: "¿Se dio de baja?", clase: "text-status-warning" },
  pendiente: { texto: "Pendiente", clase: "text-ink-secondary" },
  llego: { texto: "Llegó", clase: "text-status-success" },
};
const CICLO_DIAS = { mensual: 30, bimestral: 60, trimestral: 90 } as const;

function enlaceCompra(f: FilaTablero) {
  return `/compras/nueva?${new URLSearchParams({ idContacto: String(f.idContacto), proveedor: f.proveedor })}`;
}

function Fila({ f }: { f: FilaTablero }) {
  const cache = useQueryClient();
  const [abierta, setAbierta] = useState(false);
  const [motivo, setMotivo] = useState("");
  const refrescar = () => cache.invalidateQueries({ queryKey: ["facturas-faltantes"] });
  const perfil = useMutation({ mutationFn: (cicloDias: 30 | 60 | 90 | null) => guardarPerfil(f.idContacto, { cicloDias, sinCiclo: false, margenDias: null }), onSuccess: refrescar });
  const sinCiclo = useMutation({ mutationFn: () => guardarPerfil(f.idContacto, { cicloDias: null, sinCiclo: true, margenDias: null }), onSuccess: refrescar });
  const baja = useMutation({ mutationFn: (si: boolean) => responderBaja(f.idContacto, si), onSuccess: refrescar });
  const descartar = useMutation({ mutationFn: (clave: string) => descartarAlarma(clave, motivo), onSuccess: () => { setMotivo(""); refrescar(); } });
  const e = ESTADOS[f.estado];
  const error = perfil.error ?? sinCiclo.error ?? baja.error ?? descartar.error;
  return <>
    <tr className="border-t border-border align-top">
      <td className="p-2"><button className="text-left underline" onClick={() => setAbierta(v => !v)}>{f.proveedor}</button>
        <span className="block text-xs text-ink-secondary">Factura {f.ciclo}{f.cicloFijado ? " (fijado a mano)" : ""}</span></td>
      <td className={`p-2 font-medium ${e.clase}`}>{e.texto}{f.cambioMonto && <span className="block text-xs text-status-warning">Cambio de monto mayor al 30%</span>}</td>
      <td className="p-2">{formatFecha(f.fechaEsperada)}</td>
      <td className="p-2 text-right">{f.montoEsperado != null ? formatMoneda(f.montoEsperado) : "—"}</td>
      <td className="p-2">{f.ultimo ? <>{f.ultimo.cantidad > 1 ? `${f.ultimo.cantidad} comprobantes` : f.ultimo.numero} · {formatFecha(f.ultimo.fecha)}<span className="block text-xs">{formatMoneda(f.ultimo.importe)}</span></> : "—"}</td>
      <td className="p-2 space-y-1">
        <Link className="block underline" href={`/finanzas/cuentas-corrientes?idContacto=${f.idContacto}`}>Ver cuenta</Link>
        {f.estado !== "llego" && <SoloLectura><Link className="block underline" href={enlaceCompra(f)}>Cargar factura</Link></SoloLectura>}
      </td>
    </tr>
    {f.pagoSinComprobante && <tr><td colSpan={6} className="px-2 pb-2 text-sm text-status-danger">
      Hay un pago de {formatMoneda(f.pagoSinComprobante.importe)} del {formatFecha(f.pagoSinComprobante.fecha)} sin comprobante de este período — a verificar.</td></tr>}
    {f.estado === "baja" && <tr><td colSpan={6} className="px-2 pb-2 text-sm"><SoloLectura><span>No factura hace 3 períodos. ¿Se dio de baja? </span>
      <button className="underline" onClick={() => baja.mutate(true)}>Sí, dejar de esperarlo</button> · <button className="underline" onClick={() => baja.mutate(false)}>No, seguir esperando</button></SoloLectura></td></tr>}
    {abierta && <tr><td colSpan={6} className="space-y-2 bg-surface-muted px-2 py-3 text-sm">
      <p>Período en curso: {formatFecha(f.periodoDesde)} al {formatFecha(f.periodoHasta)}.</p>
      {f.faltantesHistoricos.length > 0 ? <div><p className="font-medium">Períodos sin factura en los últimos 24 meses (a verificar):</p>
        <ul className="ml-4 list-disc">{f.faltantesHistoricos.map(h => <li key={h.clave}>
          Alrededor del {formatFecha(h.fechaEsperada)}{h.montoEsperado != null && ` · ≈ ${formatMoneda(h.montoEsperado)}`}
          <SoloLectura><span> · <button className="underline disabled:opacity-50" disabled={!motivo.trim() || descartar.isPending} onClick={() => descartar.mutate(h.clave)}>Descartar</button></span></SoloLectura>
        </li>)}</ul>
        <SoloLectura><label className="mt-1 block">Motivo para descartar<input className="ml-2 rounded border border-border p-1" maxLength={255} value={motivo} onChange={ev => setMotivo(ev.target.value)} placeholder="Ej.: ese mes no facturó" /></label></SoloLectura>
      </div> : <p>Sin períodos faltantes en los últimos 24 meses.</p>}
      <SoloLectura><p>Ciclo de facturación: {(["mensual", "bimestral", "trimestral"] as const).map(c =>
        <button key={c} className="mr-2 underline disabled:no-underline disabled:font-semibold" disabled={f.ciclo === c && f.cicloFijado} onClick={() => perfil.mutate(CICLO_DIAS[c])}>{c}</button>)}
        <button className="mr-2 underline" onClick={() => perfil.mutate(null)}>que lo aprenda solo</button>
        <button className="underline" onClick={() => sinCiclo.mutate()}>no factura con regularidad</button></p></SoloLectura>
      {error && <p role="alert" className="text-status-danger">{error.message}</p>}
    </td></tr>}
  </>;
}

export function TableroFacturasEsperadas() {
  const q = useQuery({ queryKey: ["facturas-faltantes", "tablero"], queryFn: fetchTablero });
  if (q.isLoading) return <p>Calculando facturas esperadas…</p>;
  if (q.isError) return <p role="alert">No se pudo calcular el tablero. <button className="underline" onClick={() => q.refetch()}>Reintentar</button></p>;
  const t = q.data!;
  return <section className="space-y-3">
    <p className="text-sm">Llegaron {t.resumen.llego} · pendientes {t.resumen.pendiente} · atrasadas {t.resumen.atrasada} · ¿baja? {t.resumen.baja}.
      Son alarmas para verificar con el comprobante, no errores confirmados.</p>
    {t.items.length === 0 ? <p>No hay proveedores que facturen con regularidad.</p> :
      <table className="w-full text-sm"><thead><tr className="text-left text-ink-secondary">
        <th className="p-2">Proveedor</th><th className="p-2">Estado</th><th className="p-2">Esperada</th><th className="p-2 text-right">Monto esperado</th>
        <th className="p-2">Última factura</th><th className="p-2" /></tr></thead>
        <tbody>{t.items.map(f => <Fila key={f.idContacto} f={f} />)}</tbody></table>}
  </section>;
}
