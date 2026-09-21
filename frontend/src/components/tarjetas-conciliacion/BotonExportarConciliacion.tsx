"use client";

import { urlReporteConciliacion } from "@/services/tarjetasResumenesApi";

/**
 * Descarga la planilla (.xlsx) de conciliaciones de resúmenes para el Estudio
 * Contable, con los mismos filtros que se están viendo (tarjeta y fecha de
 * cierre). Sin filtros incluye todos los resúmenes.
 */
export function BotonExportarConciliacion({
  idTarjeta,
  fechaCierreDesde,
  fechaCierreHasta,
}: {
  idTarjeta?: string;
  fechaCierreDesde?: string;
  fechaCierreHasta?: string;
}) {
  const hayFiltro = Boolean(idTarjeta || fechaCierreDesde || fechaCierreHasta);
  return (
    <a
      href={urlReporteConciliacion({ idTarjeta, fechaCierreDesde, fechaCierreHasta })}
      title={
        hayFiltro
          ? "Descarga la planilla de conciliaciones con los filtros aplicados (tarjeta y fecha de cierre)."
          : "Descarga la planilla de conciliaciones de todos los resúmenes. Filtrá por tarjeta o fecha de cierre para acotarla."
      }
      className="rounded-sm border border-finance px-4 py-2 text-sm text-finance hover:bg-finance-light"
    >
      Exportar a Excel
    </a>
  );
}
