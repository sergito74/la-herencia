import { formatFecha, formatMoneda } from '@/lib/format';
import type { FacturaOP } from '@/services/ordenesPagoApi';

/** Cuota que vence de una compra A Plazo (12/11/2026) y, al pasar el mouse, todas con fecha, importe y saldo. */
export function CuotasInfo({ f }: { f: FacturaOP }) {
  if (!f.cuotas || f.cuotas.length === 0) return null;
  const actual = f.cuotas.find(c => c.numero === f.cuotaActual) ?? f.cuotas[f.cuotas.length - 1];
  const detalle = f.cuotas.map(c => `Cuota ${c.numero}: ${formatFecha(c.fecha)} · ${formatMoneda(c.importe)}`
    + (c.saldo <= 0 ? ' (pagada)' : c.saldo < c.importe ? ` (resta ${formatMoneda(c.saldo)})` : '')).join(String.fromCharCode(10));
  return <span className="block cursor-help text-[11px] text-slate-700" title={detalle}>Cuota {actual.numero} de {actual.de}: {formatMoneda(actual.saldo)}</span>;
}
