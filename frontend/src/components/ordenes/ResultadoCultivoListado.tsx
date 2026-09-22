"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { formatMoneda } from "@/lib/format";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { EmptyState } from "@/components/ui/States";
import { fetchCatalogosOrdenes, fetchResultadoCultivo, urlExportarResultadoCultivo } from "@/services/ordenesApi";

/**
 * Costo por Cultivo/Campaña (Historia 6): objetivo central del módulo — suma
 * insumos (FIFO), maquinaria propia y contratistas, sin fecha de cierre
 * (FR-015), junto al costo total heredado de la campaña (compras, seguros,
 * comercialización) ya calculado por el motor de resultado agrícola existente.
 */
export function ResultadoCultivoListado() {
  const [idCultivo, setIdCultivo] = useState<number | null>(null);
  const [idCampania, setIdCampania] = useState<number | null>(null);
  const { data: catalogos } = useQuery({ queryKey: ["ordenes", "catalogos"], queryFn: fetchCatalogosOrdenes });
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["resultado-cultivo", idCultivo, idCampania],
    queryFn: () => fetchResultadoCultivo({ idCultivo, idCampania }),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          Cultivo
          <select className="mt-1 block rounded border border-border px-2 py-1.5" value={idCultivo ?? ""} onChange={(e) => setIdCultivo(Number(e.target.value) || null)}>
            <option value="">Todos</option>
            {catalogos?.cultivos.map((c) => (
              <option key={c.idCultivo} value={c.idCultivo}>
                {c.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Campaña
          <select className="mt-1 block rounded border border-border px-2 py-1.5" value={idCampania ?? ""} onChange={(e) => setIdCampania(Number(e.target.value) || null)}>
            <option value="">Todas</option>
            {catalogos?.campanias.map((c) => (
              <option key={c.idCampania} value={c.idCampania}>
                {c.nombre}
              </option>
            ))}
          </select>
        </label>
        <a
          href={urlExportarResultadoCultivo({ idCultivo, idCampania })}
          className="ml-auto rounded border border-finance px-4 py-2 text-sm text-finance hover:bg-finance-light"
        >
          Exportar a Excel
        </a>
      </div>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="No se pudo calcular el resultado." onRetry={refetch} />}
      {data && data.porCultivoCampania.length === 0 && <EmptyState message="No hay costo de órdenes de trabajo con estos filtros." />}
      {data && data.porCultivoCampania.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-ink-secondary">
              <th className="py-1">Cultivo</th>
              <th className="py-1">Campaña</th>
              <th className="py-1">Lote</th>
              <th className="py-1 text-right">Insumos</th>
              <th className="py-1 text-right">Maquinaria</th>
              <th className="py-1 text-right">Contratista</th>
              <th className="py-1 text-right">Total órdenes</th>
            </tr>
          </thead>
          <tbody>
            {data.porCultivoCampania.map((r) => (
              <tr key={`${r.idCultivo}-${r.idCampania}-${r.idLote}`} className="border-b border-border">
                <td className="py-1">{r.cultivo}</td>
                <td className="py-1">{r.campania}</td>
                <td className="py-1">{r.lote}</td>
                <td className="py-1 text-right">{formatMoneda(r.costoInsumos)}</td>
                <td className="py-1 text-right">{formatMoneda(r.costoMaquinaria)}</td>
                <td className="py-1 text-right">{formatMoneda(r.costoContratista)}</td>
                <td className="py-1 text-right font-medium">{formatMoneda(r.costoTotalOrdenes)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {data && data.resumenCampaniaHeredado.length > 0 && (
        <div className="mt-6">
          <h2 className="mb-2 text-lg font-medium">Costo total de la campaña (motor de costeo heredado)</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-ink-secondary">
                <th className="py-1">Campaña</th>
                <th className="py-1 text-right">Costo total ($)</th>
                <th className="py-1 text-right">Costo total (us$)</th>
                <th className="py-1 text-right">Margen bruto ($)</th>
              </tr>
            </thead>
            <tbody>
              {data.resumenCampaniaHeredado.map((r) => (
                <tr key={r.idCampania} className="border-b border-border">
                  <td className="py-1">{r.campania}</td>
                  <td className="py-1 text-right">{r.totalCostoPesos != null ? formatMoneda(r.totalCostoPesos) : "—"}</td>
                  <td className="py-1 text-right">{r.totalCostoDolares != null ? formatMoneda(r.totalCostoDolares, "Dolares") : "—"}</td>
                  <td className="py-1 text-right">{r.margenBrutoPesos != null ? formatMoneda(r.margenBrutoPesos) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
