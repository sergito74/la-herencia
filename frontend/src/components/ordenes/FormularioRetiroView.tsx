"use client";

import Link from "next/link";

import { FormularioRetiroDocumento } from "@/components/ordenes/FormularioRetiroDocumento";
import { urlExportarFormularioRetiro, type OrdenDetalle } from "@/services/ordenesApi";

/**
 * Formulario de Retiro (FR-008) dentro del detalle de la orden: documento con
 * numeración propia que el encargado de campo usa para preparar los insumos a entregar
 * al contratista o a la maquinaria propia. Se imprime desde su propia página (A4
 * apaisado, sin el resto de la pantalla).
 */
export function FormularioRetiroView({ orden }: { orden: OrdenDetalle }) {
  if (!orden.formularioRetiro) return null;
  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Link
          href={`/produccion/ordenes/${orden.idOrden}/retiro?imprimir=1`}
          target="_blank"
          className="rounded bg-finance px-3 py-1.5 text-sm text-white hover:opacity-90"
        >
          Imprimir / guardar PDF
        </Link>
        <a href={urlExportarFormularioRetiro(orden.idOrden)} className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken">
          Exportar a Excel
        </a>
      </div>
      <div className="overflow-x-auto rounded border border-border">
        <FormularioRetiroDocumento orden={orden} />
      </div>
    </div>
  );
}
