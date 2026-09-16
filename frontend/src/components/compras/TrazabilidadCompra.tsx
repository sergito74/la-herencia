"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchCompraTrazabilidad } from "@/services/comprasApi";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";

/**
 * Trazabilidad hacia cuenta corriente/tesorería (US3: FR-008, FR-009). Un
 * array vacío siempre se muestra como "sin movimientos asociados todavía",
 * nunca como error ni como tabla vacía sin contexto.
 */
export function TrazabilidadCompra({ idCompra }: { idCompra: number }) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["compra-trazabilidad", idCompra],
    queryFn: () => fetchCompraTrazabilidad(idCompra),
  });

  return (
    <section className="rounded-md border border-border bg-surface p-4">
      <h3 className="text-sm font-semibold text-ink-primary">
        Movimientos de cuenta corriente / tesorería
      </h3>

      {isLoading && (
        <div className="mt-2">
          <LoadingState rows={2} />
        </div>
      )}

      {isError && (
        <div className="mt-2">
          <ErrorState
            message="Ocurrió un error al cargar la trazabilidad."
            onRetry={() => refetch()}
          />
        </div>
      )}

      {data && data.movimientos.length === 0 && (
        <div className="mt-2">
          <EmptyState message="Sin movimientos asociados todavía." />
        </div>
      )}

      {data && data.movimientos.length > 0 && (
        <div className="mt-2 overflow-x-auto">
          <table className="min-w-full divide-y divide-border text-sm">
            <thead className="bg-surface-sunken text-left">
              <tr>
                <th className="px-3 py-1.5 font-medium text-ink-secondary">Fecha</th>
                <th className="px-3 py-1.5 font-medium text-ink-secondary">Origen</th>
                <th className="px-3 py-1.5 font-medium text-ink-secondary">Documento</th>
                <th className="px-3 py-1.5 font-medium text-ink-secondary">Tipo</th>
                <th className="px-3 py-1.5 font-medium text-ink-secondary">Importe</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.movimientos.map((mov, index) => (
                <tr key={`${mov.idOrigen}-${index}`} className="hover:bg-surface-sunken">
                  <td className="px-3 py-1.5 font-data">{mov.fecha ?? "—"}</td>
                  <td className="px-3 py-1.5">{mov.origenTipo ?? "—"}</td>
                  <td className="px-3 py-1.5">{mov.documento ?? "—"}</td>
                  <td className="px-3 py-1.5">{mov.tipoImporte ?? "—"}</td>
                  <td className="px-3 py-1.5 font-data">{mov.importe ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
