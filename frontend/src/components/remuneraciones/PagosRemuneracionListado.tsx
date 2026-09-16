"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchPagosRemuneracion } from "@/services/remuneracionesApi";

/**
 * Listado independiente de pagos de remuneraciones (005 US2: FR-002).
 * NO se vincula a un empleado ni a una liquidación específica: no existe
 * una clave confiable para esa relación (confirmado contra datos reales,
 * ver research.md) — el sistema MUST NOT sugerir esa relación en la UI.
 */
export function PagosRemuneracionListado() {
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["remuneraciones-pagos", page],
    queryFn: () => fetchPagosRemuneracion({ page, pageSize }),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        Pagos efectivos de remuneraciones. Listado independiente — no existe una
        relación confiable en los datos de origen hacia un empleado o liquidación
        específica.
      </p>

      {isLoading && <p className="text-slate-600">Cargando…</p>}
      {isError && <p className="text-red-700">Ocurrió un error al buscar pagos.</p>}

      {data && data.items.length === 0 && (
        <p className="rounded border border-slate-200 bg-white p-6 text-center text-slate-600">
          Sin pagos registrados.
        </p>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-100 text-left">
                <tr>
                  <th className="px-3 py-2">Fecha</th>
                  <th className="px-3 py-2">Cuenta</th>
                  <th className="px-3 py-2">Caja</th>
                  <th className="px-3 py-2 text-right">Importe</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((p) => (
                  <tr key={p.idPago} className="hover:bg-slate-50">
                    <td className="px-3 py-2">{p.fecha ?? "—"}</td>
                    <td className="px-3 py-2">{p.cuenta ?? "—"}</td>
                    <td className="px-3 py-2">{p.caja ?? "—"}</td>
                    <td className="px-3 py-2 text-right">
                      {p.importe != null ? p.importe.toLocaleString("es-AR") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between text-sm text-slate-600">
            <span>
              Página {data.page} de {totalPages} — {data.total} pagos
            </span>
            <div className="flex gap-2">
              <button
                className="rounded border border-slate-300 px-3 py-1 disabled:opacity-40"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Anterior
              </button>
              <button
                className="rounded border border-slate-300 px-3 py-1 disabled:opacity-40"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Siguiente
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
