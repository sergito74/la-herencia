"use client";

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { fetchFiscalArca, fetchDetalleFiscalArca, urlFiscalArca } from '@/services/arcaApi';
import { formatFecha, formatMoneda } from '@/lib/format';
import { ErrorState, LoadingState } from '@/components/ui/States';

const monto = (value: string) => formatMoneda(Number(value));
const periodo = (value: string) => value.slice(4, 6) === '00' ? value.slice(0, 4) : `${value.slice(4, 6)}/${value.slice(0, 4)}`;

export function ArcaFiscal() {
  const [impuesto, setImpuesto] = useState('GANANCIAS');
  const [seleccion, setSeleccion] = useState<number | null>(null);
  const lista = useQuery({queryKey: ['arca-fiscal', impuesto], queryFn: () => fetchFiscalArca(impuesto)});
  const id = seleccion ?? lista.data?.items[0]?.id;
  const detalle = useQuery({queryKey: ['arca-fiscal-detalle', id], queryFn: () => fetchDetalleFiscalArca(id!), enabled: id !== undefined});
  const d = detalle.data;
  return <section aria-label="Cuenta fiscal SCT" className="space-y-4">
    <h3 className="text-lg font-semibold">Cuenta fiscal del SCT</h3>
    <p className="text-sm text-ink-secondary">Extractos del organismo a su fecha de consulta. Los saldos se leen por concepto y período; no se suman entre períodos ni al mayor financiero.</p>
    <p className="text-sm text-ink-secondary">El corte financiero de la cuenta no filtra estos extractos: pueden incluir presentaciones, pagos o compensaciones posteriores.</p>
    <div className="flex flex-wrap gap-4">
      <label className="text-sm">Impuesto<select aria-label="Impuesto fiscal" value={impuesto} onChange={e => {setImpuesto(e.target.value); setSeleccion(null);}} className="ml-2 rounded border border-border bg-surface p-2">
        <option value="GANANCIAS">Ganancias Sociedades</option><option value="SICORE">SICORE Ganancias</option><option value="IVA">IVA</option>
      </select></label>
      {lista.data && lista.data.items.length > 0 && <label className="text-sm">Extracto<select aria-label="Extracto fiscal" value={id} onChange={e => setSeleccion(Number(e.target.value))} className="ml-2 max-w-full rounded border border-border bg-surface p-2">
        {lista.data.items.map(e => <option key={e.id} value={e.id}>{periodo(e.periodo)} · {e.fuente.replace('SCT-', '').replace('-movimientos.txt', '')}{e.incompleto ? ' · incompleto' : ''}</option>)}
      </select></label>}
    </div>
    {(lista.isLoading || detalle.isLoading && id !== undefined) && <LoadingState />}
    {lista.isError && <ErrorState message={lista.error.message} />}
    {detalle.isError && id !== undefined && <ErrorState message={detalle.error.message} />}
    {lista.data?.items.length === 0 && <p>Sin extractos fiscales registrados para este impuesto.</p>}
    {d && id !== undefined && <>
      <div className="flex flex-wrap items-center gap-4 text-sm"><strong>{d.impuesto} · período {periodo(d.periodo)}</strong><span>Consultado el {formatFecha(d.fechaConsulta)}</span>
        <a href={urlFiscalArca(d.id)} target="_blank" rel="noreferrer" className="text-finance underline">Ver copia del SCT (PDF)</a>
      </div>
      {!!d.registrosMayor?.length && <div className="text-sm"><span>Registros documentados en el mayor: </span>{d.registrosMayor.map(r => <Link key={r.idImpuesto} href={`/finanzas/impuestos?highlight=${r.idImpuesto}`} className="mr-4 text-finance underline">{r.numero} · {monto(r.importe)}</Link>)}</div>}
      {d.incompleto && <p role="status" className="rounded border border-border p-3 text-sm">Este extracto tiene apartados incompletos o diferencias con el saldo publicado. Se muestran para revisión; no acreditan una conciliación completa.</p>}
      {d.conceptos.map((c, index) => <details key={`${c.concepto}-${index}`} open={index === 0} className="rounded border border-border p-3">
        <summary className="cursor-pointer text-sm font-semibold">{c.concepto} · Saldo publicado {monto(c.saldoDeudorPublicado)} · {c.verificado ? 'Suma verificada' : c.incompleto ? 'Faltan páginas' : 'Diferencia por revisar'}</summary>
        <p className="my-2 text-xs text-ink-secondary">Signo del SCT: positivo = deuda; negativo = saldo a favor. {c.movimientos.length} movimientos conservados.{!c.verificado && ` Diferencia entre suma visible y saldo publicado: ${monto(c.diferencia)}.`}</p>
        <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr>{['Operación', 'Registración', 'Movimiento', 'Debe', 'Haber', 'Referencia al mayor'].map(h => <th key={h} className="p-2 text-left">{h}</th>)}</tr></thead>
          <tbody>{c.movimientos.map((m, i) => <tr key={i} className="border-t border-border align-top">
            <td className="whitespace-nowrap p-2">{formatFecha(m.fechaOperacion)}</td><td className="whitespace-nowrap p-2">{formatFecha(m.fechaRegistracion)}</td><td className="p-2">{m.detalle}</td>
            <td className="whitespace-nowrap p-2 text-right">{monto(m.debe)}</td><td className="whitespace-nowrap p-2 text-right">{monto(m.haber)}</td>
            <td className="p-2">{m.candidatosBancoMismoDiaImporte?.length ? <>{m.candidatosBancoMismoDiaImporte.map(b => <Link key={`${b.Origen}-${b.IdOrigen}`} href={`/finanzas/tesoreria?medio=${b.Origen === 'Galicia' ? 'galicia' : 'bna'}&highlight=${b.IdOrigen}`} className="block text-finance underline">Candidato: {b.Origen} #{b.IdOrigen}</Link>)}<span className="text-xs text-ink-secondary">Misma fecha e importe; confirmar VEP.</span></> : 'Sin vínculo bancario confirmado'}</td>
          </tr>)}{c.movimientos.length === 0 && <tr><td colSpan={6} className="p-3">Sin movimientos en la copia conservada.</td></tr>}</tbody></table></div>
      </details>)}
    </>}
  </section>;
}
