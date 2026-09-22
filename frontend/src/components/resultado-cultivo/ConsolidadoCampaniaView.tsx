"use client";

import Link from "next/link";

import { KpiCard } from "@/components/ui/KpiCard";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatCantidad, formatMoneda, formatPorcentaje } from "@/lib/format";
import { urlExportarCampania, type ResultadoCampania } from "@/services/resultadoCultivoApi";

export function ConsolidadoCampaniaView({
  datos,
  cargando,
  error,
  onReintentar,
  idCultivoSeleccionado,
}: {
  datos: ResultadoCampania | undefined;
  cargando: boolean;
  error: boolean;
  onReintentar: () => void;
  idCultivoSeleccionado: number | null;
}) {
  if (error) return <ErrorState message="No se pudo cargar el resultado de la campaña." onRetry={onReintentar} />;
  if (cargando) return <LoadingState rows={6} />;
  if (!datos) return <EmptyState message="Elegí una campaña para consultar sus resultados." />;

  const cultivos = idCultivoSeleccionado
    ? datos.cultivos.filter((item) => item.idCultivo === idCultivoSeleccionado)
    : datos.cultivos;
  const sinResultados = datos.cultivos.length === 0;

  return (
    <section aria-label={`Resultado de la campaña ${datos.campania}`}>
      <h2 className="text-lg font-semibold">Campaña {datos.campania}</h2>
          {datos.costoSinClasificar && (
            <div className="mt-4 rounded border border-border bg-surface p-4">
              <h3 className="font-medium">Costos sin clasificar</h3>
              <p className="mt-1 text-sm text-ink-secondary">{datos.costoSinClasificar.motivo}</p>
              <p className="mt-2 font-data">
                {formatMoneda(datos.costoSinClasificar.montoPesos)} · {formatMoneda(datos.costoSinClasificar.montoDolares, "Dolares")}
              </p>
            </div>
          )}
      {sinResultados ? (
        <div className="mt-4">
          <EmptyState message="Esta campaña todavía no tiene información cargada." />
        </div>
      ) : (
        <>
          {datos.costeoDolaresIncompleto && (
            <p role="note" className="mt-4 rounded border border-border bg-surface-sunken p-3 text-sm">
              Costos en dólares parciales: hay costos sin importe histórico en dólares.
              El total, costo por hectárea, margen y rentabilidad en dólares usan solo los importes disponibles y no representan el resultado completo.
            </p>
          )}
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <KpiCard label="Superficie sembrada" value={`${formatCantidad(datos.superficieSembrada)} ha`} />
            <KpiCard
              label={`Superficie cosechada${datos.superficieCosechadaCompleta ? "" : " · parcial"}`}
              value={datos.superficieCosechada === null ? "—" : `${formatCantidad(datos.superficieCosechada)} ha`}
            />
            <KpiCard label="Superficie picada" value={datos.superficiePicada === null ? "—" : `${formatCantidad(datos.superficiePicada)} ha`} />
            <KpiCard label="Costo total · pesos" value={formatMoneda(datos.costoTotalPesos)} />
            <KpiCard label="Costo total · dólares" value={formatMoneda(datos.costoTotalDolares, "Dolares")} />
            <KpiCard
              label="Costo/ha sembrada · pesos"
              value={datos.costoPorHectareaSembradaPesos === null ? "—" : formatMoneda(datos.costoPorHectareaSembradaPesos)}
            />
            <KpiCard
              label="Costo/ha sembrada · dólares"
              value={datos.costoPorHectareaSembradaDolares === null ? "—" : formatMoneda(datos.costoPorHectareaSembradaDolares, "Dolares")}
            />
            <KpiCard
              label="Costo/ha cosechada · pesos"
              value={datos.costoPorHectareaCosechadaPesos === null ? "—" : formatMoneda(datos.costoPorHectareaCosechadaPesos)}
            />
            <KpiCard
              label="Costo/ha cosechada · dólares"
              value={datos.costoPorHectareaCosechadaDolares === null ? "—" : formatMoneda(datos.costoPorHectareaCosechadaDolares, "Dolares")}
            />
            <KpiCard label="Venta neta · pesos" value={formatMoneda(datos.ventaNetaPesos)} />
            <KpiCard label="Venta neta · dólares" value={formatMoneda(datos.ventaNetaDolares, "Dolares")} />
            <KpiCard label="Margen bruto · pesos" value={formatMoneda(datos.margenBrutoPesos)} />
            <KpiCard label="Margen bruto · dólares" value={formatMoneda(datos.margenBrutoDolares, "Dolares")} />
            <KpiCard
              label="Rentabilidad · pesos"
              value={datos.rentabilidadPesos === null ? "—" : formatPorcentaje(datos.rentabilidadPesos)}
            />
            <KpiCard
              label="Rentabilidad · dólares"
              value={datos.rentabilidadDolares === null ? "—" : formatPorcentaje(datos.rentabilidadDolares)}
            />
          </div>

          <div className="mt-4 flex justify-end">
            <a className="rounded border border-border bg-surface px-3 py-2 text-sm font-medium text-finance hover:bg-surface-sunken" href={urlExportarCampania(datos.idCampania)}>
              Exportar a Excel
            </a>
          </div>



          <div className="mt-6 overflow-x-auto rounded border border-border bg-surface">
            <table className="w-full min-w-[760px] border-collapse text-left text-sm">
              <thead className="bg-surface-sunken text-xs uppercase text-ink-secondary">
                <tr>
                  <th className="px-3 py-2">Cultivo</th>
                  <th className="px-3 py-2 text-right">Sembrado</th>
                  <th className="px-3 py-2 text-right">Costo · $</th>
                  <th className="px-3 py-2 text-right">Costo · us$</th>
                  <th className="px-3 py-2 text-right">Venta neta · $</th>
                  <th className="px-3 py-2 text-right">Margen · $</th>
                  <th className="px-3 py-2">Observación</th>
                </tr>
              </thead>
              <tbody>
                {cultivos.map((cultivo) => (
                  <tr key={cultivo.idCultivo} className="border-t border-border hover:bg-surface-sunken">
                    <td className="px-3 py-2 font-medium">
                      <Link
                        className="text-finance underline"
                        href={`/produccion/resultado-cultivo/${datos.idCampania}/${cultivo.idCultivo}`}
                      >
                        {cultivo.cultivo}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-right font-data">{formatCantidad(cultivo.superficieSembrada)} ha</td>
                    <td className="px-3 py-2 text-right font-data">{formatMoneda(cultivo.costoTotalPesos)}</td>
                    <td className="px-3 py-2 text-right font-data">{formatMoneda(cultivo.costoTotalDolares, "Dolares")}</td>
                    <td className="px-3 py-2 text-right font-data">{formatMoneda(cultivo.ventaNetaPesos)}</td>
                    <td className="px-3 py-2 text-right font-data">{formatMoneda(cultivo.margenBrutoPesos)}</td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        {cultivo.supCosechaEstimada && (
                          <span title="La superficie cosechada fue estimada automáticamente y necesita revisión.">
                            <StatusBadge label="Cosecha estimada" tone="warning" />
                          </span>
                        )}
                        {cultivo.advertenciaMargenNoRepresentativo && (
                          <span title="El costo registrado es menor al 20% de la venta neta; el margen puede estar incompleto.">
                            <StatusBadge label="Costos incompletos" tone="warning" />
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {cultivos.length === 0 && (
                  <tr><td colSpan={7} className="px-3 py-6 text-center text-ink-secondary">No hay resultados para ese cultivo.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
