"use client";

import { formatMonto } from "@/lib/format";
import type { PeriodoResumen, UltimaCarga } from "@/services/flujoCajaApi";

function Monto({ value }: { value: number }) {
  return <span className={value < 0 ? "text-status-danger" : undefined}>{formatMonto(value)}</span>;
}

function formatFechaCorta(fecha: string | null): string {
  if (!fecha) return "sin datos cargados";
  return new Date(fecha).toLocaleDateString("es-AR");
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
    return <p className="text-sm text-ink-secondary">No hay movimientos en el período seleccionado.</p>;
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-ink-secondary">
        Última carga:{" "}
        {ultimaCarga.map((u, i) => (
          <span key={`${u.banco}-${u.numeroCuenta}`}>
            {i > 0 && " · "}
            {u.banco} {u.numeroCuenta}: {formatFechaCorta(u.fecha)}
          </span>
        ))}
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-ink-secondary">
              <th className="py-1.5 pr-4">Período</th>
              {cuentas.map((c) => (
                <th key={`${c.banco}-${c.numeroCuenta}`} className="px-2 py-1.5 text-right">
                  {c.banco} {c.numeroCuenta}
                </th>
              ))}
              <th className="px-2 py-1.5 text-right font-semibold">Neto total</th>
            </tr>
          </thead>
          <tbody>
            {periodos.map((periodo) => (
              <tr key={periodo.periodo} className="border-t border-border">
                <td className="py-1.5 pr-4 font-medium">{periodo.periodo}</td>
                {cuentas.map((c) => {
                  const cuenta = periodo.porCuenta.find(
                    (x) => x.banco === c.banco && x.numeroCuenta === c.numeroCuenta
                  );
                  return (
                    <td key={`${c.banco}-${c.numeroCuenta}`} className="px-2 py-1.5 text-right">
                      {cuenta ? (
                        <button
                          type="button"
                          className="tabular-nums underline decoration-dotted hover:decoration-solid"
                          onClick={() => onVerDetalle(periodo.periodo, c)}
                        >
                          <Monto value={cuenta.neto} />
                        </button>
                      ) : (
                        <span className="text-ink-secondary">—</span>
                      )}
                    </td>
                  );
                })}
                <td className="px-2 py-1.5 text-right font-semibold">
                  <button
                    type="button"
                    className="tabular-nums underline decoration-dotted hover:decoration-solid"
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
          <thead>
            <tr className="text-left text-xs text-ink-secondary">
              <th className="py-1 pr-4">Período</th>
              <th className="px-2 py-1 text-right">Total interno</th>
            </tr>
          </thead>
          <tbody>
            {periodos.map((periodo) => (
              <tr key={periodo.periodo} className="border-t border-border">
                <td className="py-1 pr-4">{periodo.periodo}</td>
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
