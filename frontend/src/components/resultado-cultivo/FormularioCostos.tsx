"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatCantidad, formatFecha } from "@/lib/format";
import { fetchDetalleRubro, fetchFormularioCostos } from "@/services/resultadoCultivoApi";

import { ar, celdaNum, Dato, SelectorCultivoCampania, TablaCostosDirectos, Titulo, us } from "./FormularioAccess";

/** Costos por cultivo / campaña con el diseño y los cálculos del formulario FrmCostos de Access. */
export function FormularioCostos() {
  const [idCultivo, setIdCultivo] = useState<number | null>(null);
  const [idCampania, setIdCampania] = useState<number | null>(null);
  const [rubro, setRubro] = useState<{ id: number; concepto: string } | null>(null);
  const listo = idCultivo !== null && idCampania !== null;
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["access-costos", idCultivo, idCampania],
    queryFn: () => fetchFormularioCostos(idCultivo as number, idCampania as number), enabled: listo,
  });
  const detalle = useQuery({
    queryKey: ["access-costos-detalle", idCultivo, idCampania, rubro?.id],
    queryFn: () => fetchDetalleRubro(idCultivo as number, idCampania as number, rubro!.id), enabled: listo && !!rubro,
  });

  return (
    <div className="space-y-3">
      <SelectorCultivoCampania idCultivo={idCultivo} idCampania={idCampania}
        onCultivo={(id) => { setIdCultivo(id); setRubro(null); }} onCampania={(id) => { setIdCampania(id); setRubro(null); }}>
        {data && !data.sinSuperficie && <span className="ml-auto">Inicio cultivo: <strong>{formatFecha(data.fechaInicio ?? null)}</strong></span>}
      </SelectorCultivoCampania>

      {!listo && <p className="text-sm text-ink-secondary">Elegí cultivo y campaña.</p>}
      {listo && isLoading && <LoadingState />}
      {isError && <ErrorState message="No se pudieron calcular los costos." onRetry={refetch} />}
      {data?.sinSuperficie && <p className="text-sm text-status-warning">No se encontró superficie sembrada para {data.cultivo} {data.campania}.</p>}

      {data && !data.sinSuperficie && (
        <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-x-8 gap-y-1 rounded-md border border-border bg-surface px-3 py-2 text-sm">
              <Titulo cultivo={data.cultivo} campania={data.campania} />
              <Dato label="Superficie afectada">{formatCantidad(data.superficieAfectada ?? 0)} ha</Dato>
              <Dato label="Superficie sembrada">{formatCantidad(data.superficieSembrada ?? 0)} ha{data.superficieSembradaTeorica && <span className="ml-1 text-xs font-normal text-status-warning" title="Sin factura de siembra: es la superficie planificada">(teórica)</span>}</Dato>
              <Dato label="Superficie picada">{formatCantidad(data.superficiePicada ?? 0)} ha</Dato>
            </div>
            <TablaCostosDirectos filas={data.costosDirectos ?? []} seleccionado={rubro?.id}
              onConcepto={(f) => setRubro({ id: f.idRubro, concepto: f.concepto })}
              totales={[
                { label: "Costos Implantación", monto: data.implantacion },
                { label: "Costo Implantación Silo", monto: data.silo, sinHa: true },
                { label: "Totales Costos Cultivo Agrícola", monto: data.total, fuerte: true },
              ]} />
          </div>

          <section className="rounded-md border border-border bg-surface">
            <h3 className="border-b border-border bg-surface-sunken px-3 py-1.5 text-sm font-semibold">
              Detalles Costos{rubro ? ` · ${rubro.concepto}` : ""}
            </h3>
            {!rubro && <p className="px-3 py-3 text-sm text-ink-secondary">Clic en un concepto para ver sus comprobantes.</p>}
            {rubro && detalle.isLoading && <LoadingState />}
            {rubro && detalle.data && (
              <div className="max-h-[calc(100vh-16rem)] overflow-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-surface text-xs text-ink-secondary">
                    <tr className="border-b border-border">
                      <th className="px-2 py-1 text-right font-medium">Cantidad</th>
                      <th className="px-2 py-1 text-left font-medium">Producto / Servicio</th>
                      <th className="px-2 py-1 text-right font-medium">P. unit. AR$</th>
                      <th className="px-2 py-1 text-right font-medium">P. unit. US$</th>
                      <th className="px-2 py-1 text-right font-medium">Total AR$</th>
                      <th className="px-2 py-1 text-right font-medium">Total US$</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detalle.data.map((d, i) => (
                      <tr key={i} className="border-b border-border">
                        <td className={celdaNum}>{formatCantidad(d.cantidad)}</td>
                        <td className="px-2 py-1">{d.producto}</td>
                        <td className={celdaNum}>{ar(d.unitarioPesos)}</td>
                        <td className={celdaNum}>{us(d.unitarioDolares)}</td>
                        <td className={celdaNum}>{ar(d.totalPesos)}</td>
                        <td className={celdaNum}>{us(d.totalDolares)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t-2 border-ink-secondary/40 font-semibold">
                      <td colSpan={4} className="px-2 py-1">Total</td>
                      <td className={celdaNum}>{ar(detalle.data.reduce((s, d) => s + d.totalPesos, 0))}</td>
                      <td className={celdaNum}>{us(detalle.data.reduce((s, d) => s + d.totalDolares, 0))}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
