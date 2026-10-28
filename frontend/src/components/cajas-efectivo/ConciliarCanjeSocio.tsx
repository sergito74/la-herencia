"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { conciliarBancoCaja, type DetalleOperacionCajaResponse } from "@/services/cajasEfectivoApi";
import { fetchMovimientos } from "@/services/tesoreriaApi";
import { formatMoneda } from "@/lib/format";

export function ConciliarCanjeSocio({ detalle }: { detalle: DetalleOperacionCajaResponse }) {
  const cache = useQueryClient();
  const [buscar, setBuscar] = useState(false);
  const [fecha, setFecha] = useState(detalle.operacion.fecha);
  const [banco, setBanco] = useState(0);
  const numero = detalle.operacion.numeroTransaccion;
  const medio = detalle.operacion.bancoPendiente!;
  const movimientos = useQuery({ queryKey: ["canje-conciliacion", medio, fecha], queryFn: () => fetchMovimientos(medio, { fechaDesde: fecha, fechaHasta: fecha, page: 1, pageSize: 200 }), enabled: buscar });
  const opciones = (movimientos.data?.items ?? []).map(m => ({
    id: "idMovimientoBNA" in m ? m.idMovimientoBNA : m.idMovimiento,
    importe: "debitos" in m ? (m.creditos ?? 0) - (m.debitos ?? 0) : m.importe ?? 0,
    texto: "concepto" in m ? m.concepto : m.descripcion,
    estado: m.estadoConciliacion,
  })).filter(m => m.importe === -Number(detalle.operacion.importe) && (!m.estado || ["sin_conciliar", "ya_reconocido"].includes(m.estado)));
  const coincide = (texto: string | null) => !!numero && !!texto?.includes(numero);
  const coincidentes = opciones.filter(m => coincide(m.texto));
  useEffect(() => { if (coincidentes.length === 1 && !banco) setBanco(coincidentes[0].id); }, [coincidentes, banco]);
  const guardar = useMutation({ mutationFn: () => conciliarBancoCaja(detalle.idOperacion, { medio, idMovimiento: banco }, detalle.version), onSuccess: async () => { await cache.invalidateQueries({ predicate: q => q.queryKey[0] !== "auth" }); } });
  return <div className="space-y-3 rounded border border-border p-3">
    <p>Transferencia pendiente de conciliar · {medio === "bna" ? "Banco Nación" : medio === "galicia" ? "Galicia" : "Mercado Pago"}.</p>
    {numero && <p>Transacción bancaria N° {numero}.</p>}
    <p>El canje ya está registrado. Cuando cargues el resumen, vinculá la transferencia aquí.</p>
    {!buscar ? <button className="rounded border border-border p-2" onClick={() => setBuscar(true)}>Conciliar con el resumen bancario</button> : <>
      <label className="block">Fecha de la transferencia en el resumen<input className="block rounded border border-border p-2" type="date" value={fecha} onChange={e => { setFecha(e.target.value); setBanco(0); }} /></label>
      {movimientos.isFetching && <p>Buscando transferencias…</p>}
      {movimientos.isError && <p role="alert">No se pudieron cargar las transferencias. <button onClick={() => movimientos.refetch()}>Reintentar</button></p>}
      {!movimientos.isFetching && !movimientos.isError && opciones.length === 0 && <p>No hay transferencias disponibles por este importe en esa fecha. Podés revisar la fecha o conciliar después de cargar el resumen.</p>}
      <label className="block">Transferencia al socio<select className="block w-full rounded border border-border p-2" value={banco} onChange={e => setBanco(Number(e.target.value))}><option value={0}>Elegir transferencia</option>{opciones.map(m => <option key={m.id} value={m.id}>{coincide(m.texto) ? "✓ " : ""}{m.texto} · {formatMoneda(-m.importe)}</option>)}</select></label>
      <p>Se conciliará la transferencia sin volver a registrar efectivo ni movimientos del socio.</p>
      <button className="rounded border border-border p-2 disabled:opacity-50" disabled={guardar.isPending || movimientos.isFetching || movimientos.isError || !opciones.some(m => m.id === banco)} onClick={() => guardar.mutate()}>{guardar.isPending ? "Conciliando…" : "Confirmar conciliación"}</button>
      {guardar.isError && <p role="alert">{guardar.error.message}</p>}
    </>}
  </div>;
}
