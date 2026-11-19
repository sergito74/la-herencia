"use client";

import { EmptyState } from "@/components/ui/States";
import { formatFecha, formatMonto } from "@/lib/format";
import type { PeriodoResumen, UltimaCarga } from "@/services/flujoCajaApi";

// 18/11/2026: un mes con egresos mayores que ingresos no es una alerta: el negativo va con signo, en color normal.
function Monto({ value }: { value: number }) {
  return <span>{formatMonto(value)}</span>;
}

const NOMBRE_BANCO: Record<string, string> = { BNA: "Banco Nación", Galicia: "Galicia" };
function nombreCuenta(banco: string, numero: string): string {
  if (!/^[\d-]+$/.test(numero)) return /caja/i.test(banco) ? `Caja ${numero.replace(/^caja\s*/i, "")}` : `${banco} ${numero}`;
  return `${NOMBRE_BANCO[banco] ?? banco} ···${numero.replace(/-/g, "").slice(-4)}`;
}
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
/** "2025-01" → "ene 2025"; las semanas quedan como vienen. */
function nombrePeriodo(p: string): string {
  const m = p.match(/^(\d{4})-(\d{2})$/);
  return m ? `${MESES[Number(m[2]) - 1]} ${m[1]}` : p;
}
const CELDA = "w-full rounded px-2 py-1 text-right font-data tabular-nums transition-colors hover:bg-finance-light hover:text-finance";

function formatFechaCorta(fecha: string | null): string {
  if (!fecha) return "sin datos cargados";
  return formatFecha(fecha);
}

/** Todas las cuentas que aparecen en al menos un período, en orden estable
 * (BNA por número de cuenta, después Galicia) — así la tabla no reordena
 * columnas de un período a otro. */
function cuentasOrdenadas(periodos: PeriodoResumen[]): { banco: string; numeroCuenta: string }[] {
  const vistas = new Map<string, { banco: string; numeroCuenta: string }>();
  for (const periodo of periodos) {
    for (const cuenta of periodo.porCuenta) {
      vistas.set(`${cuenta.banco}:${cuenta.numeroCuenta}`, { banco: cuenta.banco, numeroCuenta: cuenta.numeroCuenta });
    }
  }
  return Array.from(vistas.values()).sort((a, b) =>
    a.banco === b.banco ? a.numeroCuenta.localeCompare(b.numeroCuenta) : a.banco.localeCompare(b.banco)
  );
}

export function TablaFlujoCaja({
  periodos,
  ultimaCarga,
  onVerDetalle,
}: {
  periodos: PeriodoResumen[];
  ultimaCarga: UltimaCarga[];
  /** Click en una celda período×cuenta (o el total del período) — abre el drill-down (US5). */
  onVerDetalle: (periodo: string, cuenta?: { banco: string; numeroCuenta: string }) => void;
}) {
  const cuentas = cuentasOrdenadas(periodos);

  if (periodos.length === 0) {
    return <EmptyState message="No hay movimientos en el período elegido" detalle="Probá con otro período o cargá el extracto del banco en Tesorería." />;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-ink-secondary">Movimientos cargados hasta:</span>
        {ultimaCarga.map((u) => {
          const vieja = !u.fecha || new Date(u.fecha) < new Date(Date.now() - 365 * 864e5);
          return (
            <span key={`${u.banco}-${u.numeroCuenta}`} title={`${u.banco} cuenta ${u.numeroCuenta}`}
              className={`rounded-sm px-2 py-0.5 ${vieja ? "bg-surface-sunken text-ink-muted" : "bg-finance-light text-finance"}`}>
              {nombreCuenta(u.banco, u.numeroCuenta)}: {vieja ? `sin movimientos desde ${u.fecha ? u.fecha.slice(0, 4) : "—"}` : formatFechaCorta(u.fecha)}
            </span>
          );
        })}
      </div>

      <div className="overflow-auto max-h-[calc(100vh-7rem)] rounded-lg border border-border bg-surface shadow-sm">
        <table className="w-full text-sm">
          <thead className="sticky top-0 z-10 bg-surface-sunken">
            <tr className="text-left text-xs text-ink-secondary">
              <th className="px-3 py-2">Período</th>
              {cuentas.map((c) => (
                <th key={`${c.banco}-${c.numeroCuenta}`} className="whitespace-nowrap px-2 py-2 text-right font-medium" title={`${c.banco} cuenta ${c.numeroCuenta}`}>
                  {nombreCuenta(c.banco, c.numeroCuenta)}
                </th>
              ))}
              <th className="px-3 py-2 text-right font-semibold text-ink-primary">Neto del período</th>
            </tr>
          </thead>
          <tbody>
            {periodos.map((periodo) => (
              <tr key={periodo.periodo} className="border-t border-border even:bg-surface-sunken/40">
                <td className="whitespace-nowrap px-3 py-1 font-medium">{nombrePeriodo(periodo.periodo)}</td>
                {cuentas.map((c) => {
                  const cuenta = periodo.porCuenta.find(
                    (x) => x.banco === c.banco && x.numeroCuenta === c.numeroCuenta
                  );
                  return (
                    <td key={`${c.banco}-${c.numeroCuenta}`} className="px-1 py-0.5 text-right">
                      {cuenta ? (
                        <button
                          type="button"
                          className={CELDA} title="Ver los movimientos de esta cuenta en el período"
                          onClick={() => onVerDetalle(periodo.periodo, c)}
                        >
                          <Monto value={cuenta.neto} />
                        </button>
                      ) : (
                        <span className="px-2 text-ink-muted">—</span>
                      )}
                    </td>
                  );
                })}
                <td className="px-1 py-0.5 text-right font-semibold">
                  <button
                    type="button"
                    className={CELDA} title="Ver todos los movimientos del período"
                    onClick={() => onVerDetalle(periodo.periodo)}
                  >
                    <Monto value={periodo.totalNeto} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="rounded-md border border-border bg-surface-sunken p-3">
        <h3 className="text-sm font-semibold">Movimientos internos (no suman al neto)</h3>
        <p className="mt-1 text-xs text-ink-secondary">
          Transferencias entre cuentas propias e inversiones financieras (FIMA) — se muestran aparte para no
          confundir un movimiento de plata propia con un ingreso o egreso real del negocio.
        </p>
        <table className="mt-2 w-full text-sm">
          <thead className="sticky top-[53px] z-10 bg-surface">
            <tr className="text-left text-xs text-ink-secondary">
              <th className="py-1 pr-4">Período</th>
              <th className="px-2 py-1 text-right">Total interno</th>
            </tr>
          </thead>
          <tbody>
            {periodos.map((periodo) => (
              <tr key={periodo.periodo} className="border-t border-border">
                <td className="py-1 pr-4">{nombrePeriodo(periodo.periodo)}</td>
                <td className="px-2 py-1 text-right tabular-nums">
                  <Monto value={periodo.movimientosInternos.total} />
                  {periodo.sinClasificar.cantidad > 0 && (
                    <span className="ml-2 text-xs text-status-warning">
                      · {periodo.sinClasificar.cantidad} sin clasificar (
                      {formatMonto(periodo.sinClasificar.importeAbsoluto)})
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
