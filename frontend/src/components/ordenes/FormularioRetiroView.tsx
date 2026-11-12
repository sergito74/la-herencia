"use client";

import Link from "next/link";

import { FormularioRetiroDocumento } from "@/components/ordenes/FormularioRetiroDocumento";
import { urlExportarFormularioRetiro, urlPdfFormularioRetiro, type OrdenDetalle } from "@/services/ordenesApi";

/**
 * Formulario de Retiro (FR-008) dentro del detalle de la orden: documento con
 * numeración propia que el encargado de campo usa para preparar los insumos a entregar
 * al contratista o a la maquinaria propia. Se imprime desde su propia página (A4
 * apaisado, sin el resto de la pantalla).
 */
export function FormularioRetiroView({ orden }: { orden: OrdenDetalle }) {
  if (!orden.formularioRetiro) return null;
  return (
    <details className="mt-2 rounded border border-border px-3 py-1">
      <summary className="flex cursor-pointer select-none flex-wrap items-center gap-2 py-1 text-sm">
        <span className="font-semibold uppercase tracking-wide text-ink-secondary">▸ Formulario de retiro</span>
        <span className="ml-auto flex gap-2">
        <Link
          href={`/produccion/ordenes/${orden.idOrden}/retiro?imprimir=1`}
          target="_blank"
          className="rounded bg-finance px-2.5 py-1 text-xs text-white hover:opacity-90"
        >
          Imprimir
        </Link>
        <a href={urlPdfFormularioRetiro(orden.idOrden)} className="rounded border border-border px-2.5 py-1 text-xs hover:bg-surface-sunken">
          Exportar a PDF
        </a>
        <a href={urlExportarFormularioRetiro(orden.idOrden)} className="rounded border border-border px-2.5 py-1 text-xs hover:bg-surface-sunken">
          Exportar a Excel
        </a>
        </span>
      </summary>
      <div className="mb-2 overflow-x-auto rounded border border-border">
        <FormularioRetiroDocumento orden={orden} />
      </div>
    </details>
  );
}
