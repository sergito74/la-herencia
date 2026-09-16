"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchCompraTrazabilidad } from "@/services/comprasApi";

/**
 * Trazabilidad hacia cuenta corriente/tesorería (US3: FR-008, FR-009). Un
 * array vacío siempre se muestra como "sin movimientos asociados todavía",
 * nunca como error ni como tabla vacía sin contexto.
 */
export function TrazabilidadCompra({ idCompra }: { idCompra: number }) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["compra-trazabilidad", idCompra],
    queryFn: () => fetchCompraTrazabilidad(idCompra),
  });

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-700">
        Movimientos de cuenta corriente / tesorería
      </h3>

      {isLoading && <p className="mt-2 text-slate-600">Cargando…</p>}

      {isError && (
        <p className="mt-2 text-red-700">
          Ocurrió un error al cargar la trazabilidad: {(error as Error)?.message ?? ""}
        </p>
      )}

      {data && data.movimientos.length === 0 && (
        <p className="mt-2 italic text-slate-500">
          Sin movimientos asociados todavía.
        </p>
      )}

      {data && data.movimientos.length > 0 && (
        <div className="mt-2 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-100 text-left">
              <tr>
                <th className="px-3 py-2">Fecha</th>
                <th className="px-3 py-2">Origen</th>
                <th className="px-3 py-2">Documento</th>
                <th className="px-3 py-2">Tipo</th>
                <th className="px-3 py-2">Importe</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.movimientos.map((mov, index) => (
                <tr key={`${mov.idOrigen}-${index}`} className="hover:bg-slate-50">
                  <td className="px-3 py-2">{mov.fecha ?? "—"}</td>
                  <td className="px-3 py-2">{mov.origenTipo ?? "—"}</td>
                  <td className="px-3 py-2">{mov.documento ?? "—"}</td>
                  <td className="px-3 py-2">{mov.tipoImporte ?? "—"}</td>
                  <td className="px-3 py-2">{mov.importe ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
