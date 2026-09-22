"use client";

import { KpiCard } from "@/components/ui/KpiCard";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DetalleCostosPanel } from "@/components/resultado-cultivo/DetalleCostosPanel";
import { formatCantidad, formatMoneda, formatPorcentaje } from "@/lib/format";
import { urlExportarCultivo, type DetalleCostoItem, type ResultadoCultivo } from "@/services/resultadoCultivoApi";

export function ResultadoCultivoView({
  datos,
  costos,
  cargando,
  error,
  onReintentar,
}: {
  datos: ResultadoCultivo | undefined;
  costos: DetalleCostoItem[] | undefined;
  cargando: boolean;
  error: boolean;
  onReintentar: () => void;
}) {
  if (error) return <ErrorState message="No se pudo cargar el resultado del cultivo." onRetry={onReintentar} />;
  if (cargando) return <LoadingState rows={7} />;
  if (!datos) return <EmptyState message="No hay resultado disponible para este cultivo y campaña." />;

  const sinDatos = datos.superficieSembrada === 0 && datos.superficieCosechada === null
    && datos.rinde === null && datos.ventaNetaPesos === 0 && datos.ventaNetaDolares === 0
    && costos !== undefined && costos.length === 0;
  if (sinDatos) return <EmptyState message="Este cultivo no tiene información cargada en esta campaña." />;

  return (
    <section>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{datos.cultivo} · Campaña {datos.campania}</h2>
          <p className="mt-1 text-sm text-ink-secondary">
            La superficie sembrada sale de la planificación agrícola; el rinde usa kilos cosechados sobre hectáreas cosechadas.
          </p>
        </div>
        <a className="rounded border border-border bg-surface px-3 py-2 text-sm font-medium text-finance hover:bg-surface-sunken" href={urlExportarCultivo(datos.idCampania, datos.idCultivo)}>
          Exportar a Excel
        </a>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {datos.supCosechaEstimada && (
          <span title="La superficie cosechada fue estimada automáticamente y necesita revisión.">
            <StatusBadge label="Superficie cosechada estimada — revisar" tone="warning" />
          </span>
        )}
        {datos.advertenciaMargenNoRepresentativo && (
          <span title="El costo registrado es menor al 20% de la venta neta; el margen puede estar incompleto.">
            <StatusBadge label="Costos incompletos — margen no representativo" tone="warning" />
          </span>
        )}
      </div>

      {datos.costeoDolaresIncompleto && (
            <p role="note" className="mt-4 rounded border border-border bg-surface-sunken p-3 text-sm">
              Costos en dólares parciales: hay costos sin importe histórico en dólares.
              El total, costo por hectárea, margen y rentabilidad en dólares usan solo los importes disponibles y no representan el resultado completo.
            </p>
          )}
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Superficie sembrada" value={`${formatCantidad(datos.superficieSembrada)} ha`} />
        <KpiCard label="Superficie cosechada" value={datos.superficieCosechada === null ? "—" : `${formatCantidad(datos.superficieCosechada)} ha`} />
        <KpiCard label="Rinde" value={datos.rinde === null ? "—" : `${formatCantidad(datos.rinde)} kg/ha`} />
        <KpiCard label="Superficie picada" value={datos.superficiePicada === null ? "—" : `${formatCantidad(datos.superficiePicada)} ha`} />
        <KpiCard label="Costo total · pesos" value={formatMoneda(datos.costoTotalPesos)} />
        <KpiCard label="Costo total · dólares" value={formatMoneda(datos.costoTotalDolares, "Dolares")} />
        <KpiCard label="Costo/ha sembrada · pesos" value={datos.costoPorHectareaSembradaPesos === null ? "—" : formatMoneda(datos.costoPorHectareaSembradaPesos)} />
        <KpiCard label="Costo/ha cosechada · pesos" value={datos.costoPorHectareaCosechadaPesos === null ? "—" : formatMoneda(datos.costoPorHectareaCosechadaPesos)} />
        <KpiCard label="Costo/ha sembrada · dólares" value={datos.costoPorHectareaSembradaDolares === null ? "—" : formatMoneda(datos.costoPorHectareaSembradaDolares, "Dolares")} />
        <KpiCard label="Costo/ha cosechada · dólares" value={datos.costoPorHectareaCosechadaDolares === null ? "—" : formatMoneda(datos.costoPorHectareaCosechadaDolares, "Dolares")} />
        <KpiCard label="Venta neta · pesos" value={formatMoneda(datos.ventaNetaPesos)} />
        <KpiCard label="Venta neta · dólares" value={formatMoneda(datos.ventaNetaDolares, "Dolares")} />
        <KpiCard label="Margen bruto · pesos" value={formatMoneda(datos.margenBrutoPesos)} />
        <KpiCard label="Margen bruto · dólares" value={formatMoneda(datos.margenBrutoDolares, "Dolares")} />
        <KpiCard label="Rentabilidad · pesos" value={datos.rentabilidadPesos === null ? "—" : formatPorcentaje(datos.rentabilidadPesos)} />
        <KpiCard label="Rentabilidad · dólares" value={datos.rentabilidadDolares === null ? "—" : formatPorcentaje(datos.rentabilidadDolares)} />
      </div>

      <div className="mt-8">
        <h3 className="text-base font-semibold">Detalle de costos</h3>
        <div className="mt-3"><DetalleCostosPanel costos={costos ?? []} /></div>
      </div>
    </section>
  );
}
