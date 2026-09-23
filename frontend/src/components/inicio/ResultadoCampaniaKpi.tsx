"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { fetchCampanias, fetchResultadoCampania } from "@/services/resultadoCultivoApi";
import { KpiCard } from "@/components/ui/KpiCard";
import { formatMoneda, formatNumero, formatPorcentaje } from "@/lib/format";

/**
 * Resultado consolidado de la campaña agrícola actual (012,
 * `/api/resultado-cultivo/campania/{id}`, con `id` = `campaniaActualId` de
 * `/api/resultado-cultivo/campanias`). Estado vacío explícito si no hay
 * ninguna campaña con datos (FR-008) — nunca un número inventado. Falla de
 * forma aislada (FR-005).
 */
export function ResultadoCampaniaKpi() {
  const { data: catalogo, isError: errorCatalogo } = useQuery({
    queryKey: ["inicio-campanias"],
    queryFn: fetchCampanias,
  });

  const { data: resultado, isError: errorResultado } = useQuery({
    queryKey: ["inicio-resultado-campania", catalogo?.campaniaActualId],
    queryFn: () => fetchResultadoCampania(catalogo!.campaniaActualId),
    enabled: catalogo != null,
  });

  if (errorCatalogo || errorResultado) return null;
  if (!catalogo) return <KpiCard label="Campaña agrícola actual" value="…" />;

  if (!resultado || resultado.superficieSembrada === 0) {
    return (
      <Link href="/produccion/resultado-cultivo">
        <KpiCard label="Campaña agrícola actual" value="Sin datos de campaña" />
      </Link>
    );
  }

  return (
    <Link href="/produccion/resultado-cultivo">
      <div className="rounded-md border border-border bg-surface p-4">
        <p className="text-xs uppercase tracking-wide text-ink-secondary">
          Campaña {resultado.campania} — superficie {formatNumero(resultado.superficieSembrada)} ha
        </p>
        <p
          className={`font-data mt-1 text-2xl font-semibold ${
            resultado.margenBrutoPesos < 0 ? "text-status-danger" : "text-status-success"
          }`}
        >
          Margen bruto: {formatMoneda(resultado.margenBrutoPesos)}
        </p>
        {resultado.rentabilidadPesos != null && (
          <p className="mt-1 text-sm text-ink-secondary">
            Rentabilidad: {formatPorcentaje(resultado.rentabilidadPesos)}
          </p>
        )}
      </div>
    </Link>
  );
}
