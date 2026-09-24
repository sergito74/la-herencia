"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { TablaFlujoCaja } from "@/components/flujo-caja/TablaFlujoCaja";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { formatMonto } from "@/lib/format";
import { fetchDetalle, fetchResumen, type Granularidad } from "@/services/flujoCajaApi";

export default function FlujoCajaRealPage() {
  const [granularidad, setGranularidad] = useState<Granularidad>("mensual");
  const [detalle, setDetalle] = useState<{ periodo: string; banco?: string; numeroCuenta?: string } | null>(null);

  const resumen = useQuery({
    queryKey: ["flujo-caja-resumen", granularidad],
    queryFn: () => fetchResumen({ granularidad }),
  });

  const rangoDetalle = detalle ? rangoDelPeriodo(detalle.periodo, granularidad) : null;
  const detalleQuery = useQuery({
    queryKey: ["flujo-caja-detalle", detalle],
    queryFn: () =>
      fetchDetalle({
        fechaDesde: rangoDetalle!.desde,
        fechaHasta: rangoDetalle!.hasta,
        banco: detalle?.banco,
        numeroCuenta: detalle?.numeroCuenta,
      }),
    enabled: detalle !== null,
  });

  return (
    <main className="mx-auto max-w-5xl px-8 py-6">
      <h1 className="text-2xl font-semibold">Flujo de caja real</h1>
      <p className="mt-1 text-sm text-ink-secondary">
        Movimientos bancarios reales (BNA + Galicia) agregados por período, sin transferencias entre cuentas
        propias ni movimientos de inversión financiera mezclados en el neto.
      </p>

      <div className="mt-4 flex items-center gap-2">
        <span className="text-sm text-ink-secondary">Ver por:</span>
        <div className="inline-flex rounded-md border border-border">
          {(["mensual", "semanal"] as const).map((g) => (
            <button
              key={g}
              type="button"
              onClick={() => setGranularidad(g)}
              className={`px-3 py-1 text-sm capitalize ${
                granularidad === g ? "bg-finance-light text-finance" : "text-ink-secondary"
              }`}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6">
        {resumen.isLoading && <p className="text-sm text-ink-secondary">Cargando…</p>}
        {resumen.isError && <p className="text-sm text-status-danger">No se pudo cargar el flujo de caja.</p>}
        {resumen.data && (
          <TablaFlujoCaja
            periodos={resumen.data.periodos}
            ultimaCarga={resumen.data.ultimaCarga}
            onVerDetalle={(periodo, cuenta) =>
              setDetalle({ periodo, banco: cuenta?.banco, numeroCuenta: cuenta?.numeroCuenta })
            }
          />
        )}
      </div>

      <SideDrawer
        open={detalle !== null}
        onClose={() => setDetalle(null)}
        title={detalle ? `Movimientos — ${detalle.periodo}${detalle.numeroCuenta ? ` · ${detalle.numeroCuenta}` : ""}` : ""}
      >
        {detalleQuery.isLoading && <p className="px-4 py-3 text-sm text-ink-secondary">Cargando…</p>}
        {detalleQuery.data && (
          <ul className="divide-y divide-border">
            {detalleQuery.data.movimientos.map((m, i) => (
              <li key={i} className="px-4 py-2 text-sm">
                <div className="flex items-center justify-between">
                  <span>{new Date(m.fecha).toLocaleDateString("es-AR")}</span>
                  <span className={m.importe < 0 ? "text-status-danger" : undefined}>{formatMonto(m.importe)}</span>
                </div>
                <p className="text-xs text-ink-secondary">
                  {m.concepto || "—"} {m.contacto ? `· ${m.contacto}` : ""}
                  {m.esInterno && " · movimiento interno"}
                </p>
              </li>
            ))}
            {detalleQuery.data.movimientos.length === 0 && (
              <li className="px-4 py-3 text-sm text-ink-secondary">Sin movimientos.</li>
            )}
          </ul>
        )}
      </SideDrawer>
    </main>
  );
}

/** Convierte la clave de período ("2026-07" o "2026-W30") en un rango de
 * fechas concreto para pedir el detalle (US5). */
function rangoDelPeriodo(periodo: string, granularidad: Granularidad): { desde: string; hasta: string } {
  if (granularidad === "semanal") {
    const [anioStr, semanaStr] = periodo.split("-W");
    const anio = Number(anioStr);
    const semana = Number(semanaStr);
    const primerDiaAnio = new Date(Date.UTC(anio, 0, 1));
    const diasHastaSemana = (semana - 1) * 7 - (primerDiaAnio.getUTCDay() || 7) + 1;
    const desde = new Date(primerDiaAnio);
    desde.setUTCDate(primerDiaAnio.getUTCDate() + diasHastaSemana);
    const hasta = new Date(desde);
    hasta.setUTCDate(desde.getUTCDate() + 6);
    return { desde: desde.toISOString().slice(0, 10), hasta: hasta.toISOString().slice(0, 10) };
  }
  const [anio, mes] = periodo.split("-").map(Number);
  const desde = new Date(Date.UTC(anio, mes - 1, 1));
  const hasta = new Date(Date.UTC(anio, mes, 0));
  return { desde: desde.toISOString().slice(0, 10), hasta: hasta.toISOString().slice(0, 10) };
}
