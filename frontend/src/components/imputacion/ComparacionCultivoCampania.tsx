"use client";

import type { ComparacionCampaniaOut } from "@/services/imputacionApi";

export function ComparacionCultivoCampania({ comparacion }: { comparacion: ComparacionCampaniaOut }) {
  return (
    <div className="rounded-md border border-border p-4">
      <h2 className="text-lg font-medium">{comparacion.campania ?? `Campaña ${comparacion.idCampania}`}</h2>
      {comparacion.comparacionParcial && (
        <p className="mt-1 text-sm text-amber-600">
          Comparación parcial — todavía hay ${comparacion.costoNuevo.totalPendiente.toLocaleString("es-AR")} en propuestas
          pendientes de aprobar.
        </p>
      )}
      <table className="mt-3 w-full text-sm">
        <thead>
          <tr className="text-left text-ink-secondary">
            <th className="pb-2">Fuente</th>
            <th className="pb-2">Total (pesos)</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-t border-border">
            <td className="py-1">Motor heredado (012)</td>
            <td className="py-1">{comparacion.costoHeredado.totalPesos.toLocaleString("es-AR")}</td>
          </tr>
          <tr className="border-t border-border">
            <td className="py-1">Motor nuevo (aprobado)</td>
            <td className="py-1">{comparacion.costoNuevo.totalAprobado.toLocaleString("es-AR")}</td>
          </tr>
          <tr className="border-t border-border font-medium">
            <td className="py-1">Diferencia</td>
            <td className="py-1">
              {comparacion.diferenciaPesos.toLocaleString("es-AR")}
              {comparacion.diferenciaPorcentual !== null && ` (${comparacion.diferenciaPorcentual.toFixed(1)}%)`}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
