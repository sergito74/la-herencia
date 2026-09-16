"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchArrendamientos } from "@/services/arrendamientosApi";

/**
 * Listado de arrendamientos con sus cobros asociados (005 US3: FR-003).
 * Terminología: "Arrendamiento", nunca "Alquiler" (Nota UX de plan.md).
 * Read-only.
 */
export function ArrendamientosListado() {
  const [contacto, setContacto] = useState("");
  const [appliedContacto, setAppliedContacto] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["arrendamientos", appliedContacto, page],
    queryFn: () =>
      fetchArrendamientos({ contacto: appliedContacto || undefined, page, pageSize }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setAppliedContacto(contacto);
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="flex gap-2 rounded-lg border border-slate-200 bg-white p-4">
        <label className="flex flex-1 flex-col gap-1 text-sm">
          Contacto
          <input
            className="rounded border border-slate-300 px-2 py-1"
            value={contacto}
            onChange={(e) => setContacto(e.target.value)}
            placeholder="Razón social"
          />
        </label>
        <button
          type="submit"
          className="self-end rounded bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700"
        >
          Buscar
        </button>
      </form>

      {isLoading && <p className="text-slate-600">Cargando…</p>}
      {isError && <p className="text-red-700">Ocurrió un error al buscar arrendamientos.</p>}

      {data && data.items.length === 0 && (
        <p className="rounded border border-slate-200 bg-white p-6 text-center text-slate-600">
          Sin resultados para esta búsqueda.
        </p>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="space-y-4">
            {data.items.map((a) => (
              <div key={a.idAlquiler} className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <div>
                    <h3 className="font-semibold text-slate-900">
                      Arrendamiento — {a.contacto ?? "—"}
                    </h3>
                    <p className="text-sm text-slate-600">
                      {a.inicioPeriodo ?? "—"} a {a.finPeriodo ?? "—"}
                    </p>
                  </div>
                  <p className="text-right text-sm text-slate-600">
                    Importe total del contrato:{" "}
                    <span className="font-medium text-slate-900">
                      {a.importeTotalContrato != null
                        ? a.importeTotalContrato.toLocaleString("es-AR")
                        : "—"}
                    </span>
                  </p>
                </div>

                {a.cobros.length === 0 ? (
                  <p className="mt-3 rounded border border-slate-100 bg-slate-50 p-3 text-center text-sm text-slate-500">
                    Sin cobros registrados todavía.
                  </p>
                ) : (
                  <table className="mt-3 min-w-full divide-y divide-slate-200 text-sm">
                    <thead className="text-left text-slate-500">
                      <tr>
                        <th className="px-2 py-1">Cuota</th>
                        <th className="px-2 py-1">Vencimiento</th>
                        <th className="px-2 py-1">Estado</th>
                        <th className="px-2 py-1 text-right">Importe</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {a.cobros.map((c) => (
                        <tr key={c.idCobroAlquiler}>
                          <td className="px-2 py-1">{c.numeroCuota ?? "—"}</td>
                          <td className="px-2 py-1">{c.fechaVencimiento ?? "—"}</td>
                          <td className="px-2 py-1">{c.estado ?? "—"}</td>
                          <td className="px-2 py-1 text-right">
                            {c.importeCuota != null
                              ? c.importeCuota.toLocaleString("es-AR")
                              : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between text-sm text-slate-600">
            <span>
              Página {data.page} de {totalPages} — {data.total} arrendamientos
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
