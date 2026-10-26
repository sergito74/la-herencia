"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { Breadcrumb } from "@/components/ui/Breadcrumb";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatCantidad, formatFecha, formatMoneda } from "@/lib/format";
import { actualizarCotizaciones, fetchCotizaciones, type CotizacionDia } from "@/services/cotizacionesApi";

const DIAS_SEMANA = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];

export function CotizacionesPanel() {
  const queryClient = useQueryClient();
  const [periodo, setPeriodo] = useState(() => new Date().toISOString().slice(0, 7));

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["cotizaciones", periodo],
    queryFn: () => fetchCotizaciones({ mes: periodo }),
  });

  const act = useMutation({
    mutationFn: actualizarCotizaciones,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cotizaciones"] });
      queryClient.invalidateQueries({ queryKey: ["pastaje"] });
    },
  });

  // Cálculo de promedios mensuales
  const valoresInmag = (data ?? []).map((c) => c.inmag).filter((v): v is number => v !== null && v > 0);
  const promedioInmag = valoresInmag.length > 0 ? valoresInmag.reduce((a, b) => a + b, 0) / valoresInmag.length : null;

  const valoresDolar = (data ?? []).map((c) => c.dolarPromedioBillete).filter((v): v is number => v !== null && v > 0);
  const promedioDolar = valoresDolar.length > 0 ? valoresDolar.reduce((a, b) => a + b, 0) / valoresDolar.length : null;

  return (
    <div className="space-y-6">
      <Breadcrumb items={[{ label: "Finanzas", href: "/finanzas" }, { label: "Cotizaciones" }]} />

      <div className="flex flex-wrap items-center justify-between gap-4 rounded-md border border-border bg-surface p-4">
        <div>
          <h1 className="text-xl font-bold text-ink-primary">Cotizaciones — Dólar BNA e Índice INMAG</h1>
          <p className="text-sm text-ink-secondary">
            Series históricas oficiales utilizadas para la valuación de cuentas de socios, pastaje y operaciones.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm font-medium text-ink-primary">
            Mes:
            <input
              type="month"
              className="rounded-sm border border-border bg-surface px-2 py-1 text-sm text-ink-primary"
              value={periodo}
              onChange={(e) => setPeriodo(e.target.value)}
            />
          </label>

          <SoloLectura>
            <button
              type="button"
              disabled={act.isPending}
              onClick={() => act.mutate()}
              className="rounded-sm bg-agro px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
            >
              {act.isPending ? "Sincronizando…" : "Actualizar ahora"}
            </button>
          </SoloLectura>
        </div>
      </div>

      {/* Tarjetas de Resumen / Promedios del Mes */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-md border border-border bg-surface p-4 shadow-xs">
          <div className="text-xs font-semibold uppercase text-ink-secondary">INMAG Promedio Mensual</div>
          <div className="mt-1 text-2xl font-bold text-agro font-data">
            {promedioInmag !== null ? `$${promedioInmag.toFixed(3)}` : "—"}
          </div>
          <div className="mt-1 text-xs text-ink-secondary">
            {valoresInmag.length} días con cotización en el mes
          </div>
        </div>

        <div className="rounded-md border border-border bg-surface p-4 shadow-xs">
          <div className="text-xs font-semibold uppercase text-ink-secondary">Dólar BNA Promedio Mensual (Billete)</div>
          <div className="mt-1 text-2xl font-bold text-ink-primary font-data">
            {promedioDolar !== null ? formatMoneda(promedioDolar) : "—"}
          </div>
          <div className="mt-1 text-xs text-ink-secondary">
            Promedio oficial de días hábiles bancarios
          </div>
        </div>
      </div>

      {act.data && (
        <div className="rounded-md border border-status-success/40 bg-status-success/10 p-3 text-sm text-status-success">
          {act.data.mensaje}
        </div>
      )}

      {act.error && (
        <div className="rounded-md border border-status-danger/40 bg-status-danger/10 p-3 text-sm text-status-danger">
          Error al sincronizar: {(act.error as Error).message}
        </div>
      )}

      {isLoading && <LoadingState />}
      {isError && <ErrorState message={(error as Error).message} onRetry={() => refetch()} />}

      {data && (
        <div className="overflow-x-auto rounded-md border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-surface-sunken text-xs font-semibold uppercase text-ink-secondary">
              <tr>
                <th className="px-3 py-2">Fecha</th>
                <th className="px-3 py-2 text-right">Dólar Billete (Compra)</th>
                <th className="px-3 py-2 text-right">Dólar Billete (Venta)</th>
                <th className="px-3 py-2 text-right">Dólar Promedio</th>
                <th className="px-3 py-2 text-right">Dólar Divisa (Compra)</th>
                <th className="px-3 py-2 text-right">Dólar Divisa (Venta)</th>
                <th className="px-3 py-2 text-right">INMAG $/kg</th>
                <th className="px-3 py-2 text-right">Cabezas MAG</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.map((c) => {
                const diaIdx = new Date(`${c.fecha}T12:00:00`).getDay();
                const esFinDeSemana = diaIdx === 0 || diaIdx === 6;

                return (
                  <tr
                    key={c.fecha}
                    className={esFinDeSemana ? "bg-surface-sunken/40 text-ink-secondary" : "hover:bg-surface-sunken/20"}
                  >
                    <td className="px-3 py-2 whitespace-nowrap">
                      <span className="font-medium text-ink-primary">{formatFecha(c.fecha)}</span>
                      <span className="ml-2 text-xs text-ink-secondary">({DIAS_SEMANA[diaIdx]})</span>
                    </td>
                    <td className="px-3 py-2 text-right font-data tabular-nums">
                      {c.dolarCompraBillete != null ? formatMoneda(c.dolarCompraBillete) : "—"}
                    </td>
                    <td className="px-3 py-2 text-right font-data tabular-nums">
                      {c.dolarVentaBillete != null ? formatMoneda(c.dolarVentaBillete) : "—"}
                    </td>
                    <td className="px-3 py-2 text-right font-data font-semibold text-ink-primary tabular-nums">
                      {c.dolarPromedioBillete != null ? formatMoneda(c.dolarPromedioBillete) : "—"}
                    </td>
                    <td className="px-3 py-2 text-right font-data tabular-nums">
                      {c.dolarCompraDivisa != null ? formatMoneda(c.dolarCompraDivisa) : "—"}
                    </td>
                    <td className="px-3 py-2 text-right font-data tabular-nums">
                      {c.dolarVentaDivisa != null ? formatMoneda(c.dolarVentaDivisa) : "—"}
                    </td>
                    <td className="px-3 py-2 text-right font-data font-semibold text-agro tabular-nums">
                      {c.inmag != null ? `$${c.inmag.toFixed(3)}` : "—"}
                    </td>
                    <td className="px-3 py-2 text-right font-data tabular-nums">
                      {c.cabezasIngresadas != null && c.cabezasIngresadas > 0
                        ? formatCantidad(c.cabezasIngresadas)
                        : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
