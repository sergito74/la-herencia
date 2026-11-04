'use client';
import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { SoloLectura } from '@/components/auth/SoloLectura';
import { formatFecha, formatMoneda } from '@/lib/format';
import { facturasAPagar, type FacturaAPagar } from '@/services/ordenesPagoApi';
import { boton, campo } from './FormularioOrdenPago';

type Seleccion = { idContacto: number; proveedor: string | null; facturas: Record<number, number> };

/** Facturas a pagar de todos los proveedores, ordenadas por vencimiento (la vencida más vieja primero). Desde acá
 * se eligen las facturas de un proveedor y se arranca la orden de pago. */
export function FacturasAPagar({ idContacto, crearOrden }: { idContacto: number | null; crearOrden: (s: Seleccion) => void }) {
  const qc = useQueryClient();
  const [soloVencidas, setSoloVencidas] = useState(false);
  const [buscar, setBuscar] = useState('');
  const [sel, setSel] = useState<Seleccion | null>(null);
  const q = useQuery({ queryKey: ['facturas-a-pagar'], queryFn: () => facturasAPagar(), staleTime: 60_000 });
  const filas = useMemo(() => (q.data ?? []).filter(f =>
    (!idContacto || f.idContacto === idContacto) && (!soloVencidas || f.diasVencida > 0) &&
    (!buscar || `${f.proveedor ?? ''} ${f.numero ?? ''}`.toLowerCase().includes(buscar.toLowerCase()))), [q.data, idContacto, soloVencidas, buscar]);
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
      <table className="w-full text-sm">
        <thead className="bg-slate-50"><tr>
          <th className="p-2"></th><th className="p-2 text-left">Vencimiento</th><th className="text-left">Proveedor</th><th className="text-left">Factura</th>
          <th className="text-left">Fecha</th><th className="text-right">Saldo</th><th className="text-right">En otras órdenes</th><th className="text-right">Disponible</th>
        </tr></thead>
        <tbody>
          {filas.map(f => {
            const tildada = sel?.idContacto === f.idContacto && f.idCompra in sel.facturas;
            return <tr key={f.idCompra} className={`border-t ${tildada ? 'bg-emerald-50' : ''}`}>
              <td className="p-2"><input type="checkbox" aria-label={`Seleccionar ${f.numero ?? 'factura'} de ${f.proveedor ?? ''}`} disabled={f.disponible <= 0} checked={!!tildada} onChange={e => tildar(f, e.target.checked)} /></td>
              <td className={`p-2 ${f.diasVencida > 0 ? 'text-red-700 font-medium' : ''}`}>{formatFecha(f.vencimiento)}<span className="block text-xs text-slate-600">{f.condicion === 'Contado' ? 'Contado' : 'A plazo'}</span>{f.diasVencida > 0 && <span className="block text-xs">vencida hace {f.diasVencida} días</span>}</td>
              <td>{f.proveedor}{f.ajustado && <span className="block text-xs text-amber-800" title="Hay facturas con pagos sin vincular: se muestran solo las que explican el saldo de la cuenta">ajustado al saldo de la cuenta</span>}</td>
              <td><a className="underline" href={`/compras/${f.idCompra}/editar`}>{f.numero || 'Sin número'}</a></td>
              <td>{formatFecha(f.fecha)}</td>
              <td className="text-right">{formatMoneda(f.saldo)}</td>
              <td className="text-right">{f.reservado ? formatMoneda(f.reservado) : '—'}</td>
              <td className="text-right">{formatMoneda(f.disponible)}</td>
            </tr>;
          })}
        </tbody>
      </table>
      {!q.isLoading && filas.length === 0 && <p className="p-6 text-slate-600">No hay facturas a pagar con estos filtros.</p>}
    </section>
    <p className="text-xs text-slate-600">Importes en pesos (las facturas en dólares al tipo de cambio de la factura). El saldo de cada proveedor coincide con su cuenta corriente; el vencimiento es el de la condición de pago (A plazo: su fecha de vencimiento; Contado: la fecha de la factura).</p>
  </section>;
}
