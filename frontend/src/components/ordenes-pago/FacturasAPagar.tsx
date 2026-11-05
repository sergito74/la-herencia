'use client';
import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { SoloLectura } from '@/components/auth/SoloLectura';
import { formatFecha, formatMoneda } from '@/lib/format';
import { facturasAPagar, pagosEnCamino, type FacturaAPagar } from '@/services/ordenesPagoApi';
import { boton, campo } from './FormularioOrdenPago';

type Seleccion = { idContacto: number; proveedor: string | null; facturas: Record<number, number> };

/** Facturas a pagar de todos los proveedores, ordenadas por vencimiento (la vencida más vieja primero). Desde acá
 * se eligen las facturas de un proveedor y se arranca la orden de pago. */
export function FacturasAPagar({ idContacto, crearOrden }: { idContacto: number | null; crearOrden: (s: Seleccion) => void }) {
  const qc = useQueryClient();
  const [soloVencidas, setSoloVencidas] = useState(false);
  const [verTodas, setVerTodas] = useState(false);
  const [buscar, setBuscar] = useState('');
  const [sel, setSel] = useState<Seleccion | null>(null);
  const q = useQuery({ queryKey: ['facturas-a-pagar'], queryFn: () => facturasAPagar(), staleTime: 60_000 });
  const camino = useQuery({ queryKey: ['pagos-en-camino', q.dataUpdatedAt], queryFn: pagosEnCamino, enabled: q.isSuccess });
  const filas = useMemo(() => (q.data ?? []).filter(f =>
    (!idContacto || f.idContacto === idContacto) && (!soloVencidas || f.diasVencida > 0) && (verTodas || f.estado === 'a pagar' || f.estado === 'sueldo') &&
    (!buscar || `${f.proveedor ?? ''} ${f.numero ?? ''}`.toLowerCase().includes(buscar.toLowerCase()))), [q.data, idContacto, soloVencidas, verTodas, buscar]);
  const total = filas.reduce((a, f) => a + f.saldo, 0);
  const vencido = filas.filter(f => f.diasVencida > 0).reduce((a, f) => a + f.saldo, 0);
  const totalSel = sel ? Object.values(sel.facturas).reduce((a, b) => a + b, 0) : 0;

  function tildar(f: FacturaAPagar, on: boolean) {
    setSel(prev => {
      const base = prev && prev.idContacto === f.idContacto ? prev : { idContacto: f.idContacto, proveedor: f.proveedor, facturas: {} };
      const facturas = { ...base.facturas };
      if (on) facturas[f.idCompra] = f.disponible; else delete facturas[f.idCompra];
      return Object.keys(facturas).length ? { ...base, facturas } : null;
    });
  }

  async function recalcular() {
    await qc.fetchQuery({ queryKey: ['facturas-a-pagar'], queryFn: () => facturasAPagar(true) });
  }

  return <section className="space-y-3" aria-label="Facturas a pagar">
    <div className="rounded border bg-white p-4 flex flex-wrap items-end gap-4">
      <label className="text-sm">Buscar<input className={`${campo} block w-64`} value={buscar} placeholder="Proveedor o número" onChange={e => setBuscar(e.target.value)} /></label>
      <label className="text-sm"><input type="checkbox" checked={soloVencidas} onChange={e => setSoloVencidas(e.target.checked)} /> Solo vencidas</label>
      <label className="text-sm"><input type="checkbox" checked={verTodas} onChange={e => setVerTodas(e.target.checked)} /> Ver también lo que se paga solo (tarjeta y débitos del banco)</label>
      <button className={campo} disabled={q.isFetching} onClick={recalcular}>{q.isFetching ? 'Calculando…' : 'Recalcular'}</button>
      <p className="ml-auto text-sm"><strong>{filas.length}</strong> facturas · Total {formatMoneda(total)} · <span className="text-red-700">Vencido {formatMoneda(vencido)}</span></p>
    </div>
    {sel && <div className="sticky top-0 z-10 flex flex-wrap items-center gap-3 rounded border border-emerald-300 bg-emerald-50 p-3">
      <span><strong>{sel.proveedor}</strong> · {Object.keys(sel.facturas).length} facturas · {formatMoneda(totalSel)}</span>
      <SoloLectura><button className={boton} onClick={() => crearOrden(sel)}>Crear orden de pago</button></SoloLectura>
      <button className={campo} onClick={() => setSel(null)}>Limpiar selección</button>
      <span className="text-xs text-slate-600">Una orden es de un solo proveedor: al tildar una factura de otro, la selección cambia a ese proveedor.</span>
    </div>}
    {q.isLoading && <p>Calculando las facturas a pagar de todas las cuentas…</p>}
    {q.isError && <p role="alert" className="text-red-700">{q.error.message}</p>}
    <section className="overflow-auto rounded border bg-white">
      <table className="w-full table-fixed text-xs leading-tight">
        <colgroup><col className="w-7" /><col className="w-28" /><col className="w-44" /><col /><col className="w-20" /><col className="w-28" /><col className="w-24" /><col className="w-28" /></colgroup>
        <thead className="bg-slate-50"><tr>
          <th className="p-1"></th><th className="p-1 text-left">Vencimiento</th><th className="p-1 text-left">Proveedor</th><th className="p-1 text-left">Documento</th>
          <th className="p-1 text-left">Fecha</th><th className="p-1 text-right">Saldo</th><th className="p-1 text-right">En otras órdenes</th><th className="p-1 text-right">Disponible</th>
        </tr></thead>
        <tbody>
          {filas.map((f, i) => {
            const tildada = sel?.idContacto === f.idContacto && f.idCompra in sel.facturas;
            return <tr key={`${f.origen ?? "Compras"}-${f.idCompra}-${i}`} className={`border-t ${tildada ? 'bg-emerald-50' : ''}`}>
              <td className="p-1 align-top"><input type="checkbox" aria-label={`Seleccionar ${f.numero ?? 'factura'} de ${f.proveedor ?? ''}`} disabled={(f.origen ?? 'Compras') !== 'Compras' || f.disponible <= 0} checked={!!tildada} onChange={e => tildar(f, e.target.checked)} /></td>
              <td className={`p-1 align-top ${f.diasVencida > 0 ? 'text-red-700 font-medium' : ''}`}>{formatFecha(f.vencimiento)}<span className="block text-[11px] text-slate-600">{f.condicion === 'Contado' ? 'Contado' : 'A plazo'}</span>{f.diasVencida > 0 && <span className="block text-[11px]">vencida hace {f.diasVencida} días</span>}</td>
              <td className="p-1 align-top break-words">{f.proveedor}
                {f.estado === 'tarjeta' && <span className="block text-[11px] text-slate-600">Se paga con tarjeta: queda saldada al cargar el resumen</span>}
                {f.suspendida && <span className="block text-[11px] text-amber-800">Factura suspendida</span>}
                {f.estado === 'debito' && <span className="block text-[11px] text-slate-600">Lo debita el banco</span>}
                {f.estado === 'sueldo' && <span className="block text-[11px] text-slate-600">Sueldo</span>}
                {f.origen === 'Portal' && <span className="block text-[11px] text-slate-600">Según el portal del proveedor</span>}
                {!!f.enCamino && <span className="block text-[11px] text-slate-600">Ya se le pagaron {formatMoneda(f.enCamino)} que esperan el resumen del banco</span>}
                {(f.origen ?? 'Compras') !== 'Compras' && f.origen !== 'Portal' && <span className="block text-[11px] text-slate-600">{f.origen === 'Remuneraciones' ? 'Sueldo' : f.origen === 'Impuestos' ? 'Impuesto o tasa' : f.origen}</span>}</td>
              <td className="p-1 align-top break-words whitespace-normal">{(f.origen ?? 'Compras') === 'Compras' ? <a className="underline" href={`/compras/${f.idCompra}/editar`}>{f.numero || 'Sin número'}</a> : f.numero}</td>
              <td className="p-1 align-top">{formatFecha(f.fecha)}</td>
              <td className="p-1 align-top text-right whitespace-nowrap">{f.saldoUsd ? formatMoneda(f.saldoUsd, 'Dolares') : formatMoneda(f.saldo)}</td>
              <td className="p-1 align-top text-right whitespace-nowrap">{f.reservado ? formatMoneda(f.reservado) : '—'}</td>
              <td className="p-1 align-top text-right whitespace-nowrap">{f.saldoUsd ? formatMoneda(f.saldoUsd, 'Dolares') : (f.origen ?? 'Compras') === 'Compras' ? formatMoneda(f.disponible) : formatMoneda(f.saldo)}</td>
            </tr>;
          })}
        </tbody>
      </table>
      {!q.isLoading && filas.length === 0 && <p className="p-6 text-slate-600">No hay facturas a pagar con estos filtros.</p>}
    </section>
    {!!camino.data?.length && <section className="rounded border bg-white" aria-label="Pagos hechos que esperan el banco">
      <h3 className="p-3 font-medium">Pagados, esperando el resumen del banco</h3>
      <table className="w-full text-xs leading-tight"><thead className="bg-slate-50"><tr>
        <th className="p-2 text-left">Proveedor</th><th className="text-left">Pago</th><th className="text-left">Fecha</th><th className="text-left">Débito previsto</th><th className="text-left">Concepto</th><th className="p-2 text-right">Importe</th>
      </tr></thead><tbody>
        {camino.data.map((c, i) => <tr key={i} className="border-t">
          <td className="p-2">{c.proveedor}</td><td>{c.tipo === 'echeq' ? `eCheq ${c.cheque ?? ''}` : 'Transferencia'}</td>
          <td>{formatFecha(c.fecha)}</td><td>{formatFecha(c.fechaPago)}</td><td>{c.concepto}</td><td className="p-2 text-right">{formatMoneda(c.importe)}</td>
        </tr>)}
      </tbody></table>
      <p className="p-3 text-xs text-slate-600">Salen de los comprobantes guardados en la carpeta Cuentas a pagar. Ya están descontados de lo que se debe; se confirman solos al subir el resumen del banco.</p>
    </section>}
    <p className="text-xs text-slate-600">Importes en pesos (las facturas en dólares al tipo de cambio de la factura). Proveedores con portal (Sancor, Cooperativa, Jáuregui, Bayá Casal, Cargill): lo que el portal muestra impago. El resto: lo que debe la cuenta, menos los pagos que esperan el banco, son sus documentos más nuevos (lo pagado cubre primero lo más viejo); se pagan con tarjeta las de proveedores que se pagan así; el vencimiento es el de la condición de pago (A plazo: su fecha de vencimiento; Contado: la fecha de la factura).</p>
  </section>;
}
