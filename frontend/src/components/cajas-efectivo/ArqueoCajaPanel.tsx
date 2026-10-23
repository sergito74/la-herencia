"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { hoyCaja } from "./OperacionCajaForm";
import { listarArqueosCaja, guardarArqueoCaja, confirmarArqueoCaja, type ArqueoCaja, type CajaSlug } from "@/services/cajasEfectivoApi";
import { monedaCaja } from "@/services/cajasEfectivoApi";
import { formatFecha, formatMoneda } from "@/lib/format";

export function ArqueoCajaPanel({ caja, onOperation }: { caja: CajaSlug; onOperation: (id: number) => void }) {
  const cache = useQueryClient();
  const [page, setPage] = useState(1);
  const [fecha, setFecha] = useState(hoyCaja());
  const [denominaciones, setDenominaciones] = useState([{ valor: caja === "giamigli-dolares" ? 100 : 1000, cantidad: "0" }]);
  const [draft, setDraft] = useState<ArqueoCaja | null>(null);
  const [correctivo, setCorrectivo] = useState<number | undefined>();
  const [aceptar, setAceptar] = useState(false);
  const [aceptarAvisos, setAceptarAvisos] = useState(false);
  const data = useQuery({ queryKey: ["caja-arqueos", caja, page], queryFn: () => listarArqueosCaja(caja, page) });
  const save = useMutation({ mutationFn: () => guardarArqueoCaja(caja, {
    fechaCorte: fecha, denominaciones: denominaciones.map(d => ({ valor: d.valor.toFixed(2), cantidad: Number(d.cantidad) })),
    versionEsperada: draft?.version, idArqueoAnterior: correctivo,
  }, draft?.idArqueo), onSuccess: async a => { setDraft(a); setAceptar(false); await data.refetch(); } });
  const confirm = useMutation({ mutationFn: () => confirmarArqueoCaja(draft!, aceptar, aceptarAvisos ? ["SALDO_NEGATIVO", "PERIODO_ARQUEADO"] : []), onSuccess: async () => { setDraft(null); setCorrectivo(undefined); await cache.invalidateQueries({ predicate: q => q.queryKey[0] !== "auth" }); } });
  const total = denominaciones.reduce((sum, d) => sum + d.valor * Number(d.cantidad || 0), 0);
  const firma = (d: { valor: string; cantidad: number }[]) => JSON.stringify([...d].sort((a, b) => Number(a.valor) - Number(b.valor)));
  const dirty = draft ? fecha !== draft.fechaCorte || firma(denominaciones.map(d => ({ valor: d.valor.toFixed(2), cantidad: Number(d.cantidad) }))) !== firma(draft.denominaciones) : false;
  return <section className="space-y-3 rounded border border-border p-4"><h3 className="font-semibold">Arqueos de efectivo en {monedaCaja(caja) === "Dolares" ? "dólares" : "pesos"}</h3>
    {caja === "condominio-lsc" && <p>El registro parcial del Condominio no admite arqueos físicos.</p>}
    {data.isLoading && <p>Cargando arqueos…</p>}{data.isError && <p role="alert">{data.error.message} <button onClick={() => data.refetch()}>Reintentar</button></p>}
    {data.data?.items.length === 0 && <p>No hay arqueos registrados.</p>}
    <ul className="space-y-2">{data.data?.items.map(a => <li className="rounded border border-border p-2" key={a.idArqueo}><p>{formatFecha(a.fechaCorte)} · {a.estado} · contado {formatMoneda(Number(a.totalContado), monedaCaja(caja))} · diferencia original {formatMoneda(Number(a.diferencia), monedaCaja(caja))} · diferencia vigente {formatMoneda(Number(a.diferenciaVigenteDecimal), monedaCaja(caja))}</p>
      {a.estado !== "Confirmado" && <p>Este recuento no acredita una conciliación vigente.</p>}
      {a.idOperacionAjuste && <button className="underline" onClick={() => onOperation(a.idOperacionAjuste!)}>Ver ajuste y auditoría</button>}
      <SoloLectura>{a.estado === "Borrador" ? <button className="ml-3 underline" onClick={() => { setDraft(a); setFecha(a.fechaCorte); setDenominaciones(a.denominaciones.map(d => ({ valor: Number(d.valor), cantidad: String(d.cantidad) }))); setCorrectivo(a.idArqueoAnterior ?? undefined); setAceptar(false); }}>Continuar borrador</button> : a.estado !== "Confirmado" && <button className="ml-3 underline" onClick={() => { setDraft(null); setCorrectivo(a.idArqueo); setFecha(hoyCaja()); }}>Nuevo arqueo correctivo</button>}</SoloLectura>
    </li>)}</ul>
    {!!data.data && data.data.total > data.data.pageSize && <div><button disabled={page === 1} onClick={() => setPage(p => p - 1)}>Anterior</button> · {page} · <button disabled={page * data.data.pageSize >= data.data.total} onClick={() => setPage(p => p + 1)}>Siguiente</button></div>}
    <SoloLectura><form className="space-y-3 border-t border-border pt-3" onSubmit={e => { e.preventDefault(); save.mutate(); }}><h4>{draft ? `Borrador ${draft.idArqueo}` : "Nuevo recuento"}{correctivo ? ` · corrige arqueo ${correctivo}` : ""}</h4>
      <label>Fecha de corte<input type="date" className="ml-2 rounded border border-border p-2" value={fecha} required onChange={e => { setFecha(e.target.value); }} /></label>
      {denominaciones.map((d, i) => <div key={i} className="flex flex-wrap items-end gap-3"><label>Denominación<MoneyInput className="rounded border border-border p-2" moneda={monedaCaja(caja)} value={d.valor} onChange={v => setDenominaciones(prev => prev.map((x, k) => k === i ? { ...x, valor: v } : x))} /></label><label>Cantidad<input className="block w-28 rounded border border-border p-2" type="text" inputMode="numeric" pattern="[0-9]+" required value={d.cantidad} onChange={e => setDenominaciones(prev => prev.map((x, k) => k === i ? { ...x, cantidad: e.target.value } : x))} /></label>{denominaciones.length > 1 && <button type="button" onClick={() => setDenominaciones(prev => prev.filter((_, k) => k !== i))}>Quitar</button>}</div>)}
      <button type="button" className="underline" onClick={() => setDenominaciones(prev => [...prev, { valor: 0, cantidad: "0" }])}>Agregar denominación</button><p>Total contado: {formatMoneda(total, monedaCaja(caja))}</p>
      <button className="rounded border border-border p-2 disabled:opacity-50" disabled={save.isPending}>{save.isPending ? "Guardando…" : "Guardar borrador y comparar"}</button>
    </form>
    {draft && <div className="space-y-2 rounded border border-border p-3"><p>Sistema al corte: {formatMoneda(Number(draft.saldoRecalculadoDecimal), monedaCaja(caja))} · contado: {formatMoneda(Number(draft.totalContado), monedaCaja(caja))} · diferencia: {formatMoneda(Number(draft.diferenciaVigenteDecimal), monedaCaja(caja))}</p>
      {dirty && <p>Hay cambios sin guardar. Guardá de nuevo el borrador antes de confirmar.</p>}
      <label className="block"><input type="checkbox" checked={aceptar} onChange={e => setAceptar(e.target.checked)} /> Confirmo el recuento y, si corresponde, su diferencia de arqueo.</label>
      {!!draft.advertencias?.length && <label className="block"><input type="checkbox" checked={aceptarAvisos} onChange={e => setAceptarAvisos(e.target.checked)} /> Confirmo las advertencias: {draft.advertencias.map(w => w === "SALDO_NEGATIVO" ? "saldo negativo" : "período arqueado afectado").join(", ")}.</label>}
      <button className="rounded border border-border p-2 disabled:opacity-50" disabled={!aceptar || dirty || confirm.isPending || (!!draft.advertencias?.length && !aceptarAvisos)} onClick={() => confirm.mutate()}>{confirm.isPending ? "Confirmando…" : "Confirmar arqueo"}</button>
    </div>}
    {(save.error || confirm.error) && <p className="text-status-danger" role="alert">{(save.error || confirm.error)?.message}</p>}</SoloLectura>
  </section>;
}
