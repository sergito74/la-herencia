"use client";

import { formatCantidad } from "@/lib/format";
import { urlExportarFormularioRetiro, type OrdenDetalle } from "@/services/ordenesApi";

/**
 * Formulario de Retiro (FR-008): documento con numeración propia que el
 * encargado de campo usa para preparar los insumos a entregar al contratista
 * o a la maquinaria propia.
 */
export function FormularioRetiroView({ orden }: { orden: OrdenDetalle }) {
  if (!orden.formularioRetiro) return null;
  return (
    <div className="rounded border border-border p-4 print:border-0">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-lg font-semibold">Formulario de Retiro N° {orden.formularioRetiro.idFormularioRetiro}</h2>
        <span className="text-sm text-ink-secondary">Orden N° {orden.idOrden} — {orden.fechaPedido}</span>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-ink-secondary">
            <th className="py-1">Producto</th>
            <th className="py-1 text-right">Cantidad</th>
            <th className="py-1">Unidad</th>
          </tr>
        </thead>
        <tbody>
          {orden.insumos.map((r) => (
            <tr key={r.idOrdenInsumo} className="border-b border-border">
              <td className="py-1">{r.producto ?? r.idProducto}</td>
              <td className="py-1 text-right">{formatCantidad(r.cantidadTotal)}</td>
              <td className="py-1">{r.unidad}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-3 flex gap-2 print:hidden">
        <button type="button" onClick={() => window.print()} className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken">
          Imprimir
        </button>
        <a href={urlExportarFormularioRetiro(orden.idOrden)} className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken">
          Exportar a Excel
        </a>
      </div>
    </div>
  );
}
