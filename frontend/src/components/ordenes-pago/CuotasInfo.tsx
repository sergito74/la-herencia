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

/** Importe sugerido para pagar una factura (12/11/2026): si tiene cuotas, lo que vence hasta la fecha de pago (y si
 * no vence ninguna, la próxima cuota); si no, todo lo disponible. Nunca más que lo disponible. */
export function importeSugerido(f: FacturaOP, fechaPago: string): number {
  if (!f.cuotas || f.cuotas.length < 2) return f.disponible;
  const vencidas = f.cuotas.filter(c => c.saldo > 0 && c.fecha.slice(0, 10) <= fechaPago).reduce((a, c) => a + c.saldo, 0);
  const proxima = f.cuotas.find(c => c.saldo > 0)?.saldo ?? f.disponible;
  return Math.min(f.disponible, Math.round((vencidas > 0 ? vencidas : proxima) * 100) / 100);
}

/** La cuota que se paga es el adelanto (cuota 1 sin pagos): la retención se descuenta en la cuota 2. */
export const esAdelanto = (f: FacturaOP) => (f.cuotas?.length ?? 0) > 1 && f.cuotaActual === 1 && f.pagado <= 0;
