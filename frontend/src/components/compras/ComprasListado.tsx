"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { fetchCompras } from "@/services/comprasApi";

/**
 * Search + results table for compras (US1: FR-001, FR-002, FR-012, FR-013).
 * Read-only: no create/edit/delete affordance exists here (FR-010).
 */
export function ComprasListado() {
  const [proveedor, setProveedor] = useState("");
  const [numeroDocumento, setNumeroDocumento] = useState("");
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const [appliedFilters, setAppliedFilters] = useState({
    proveedor: "",
    numeroDocumento: "",
    fechaDesde: "",
    fechaHasta: "",
  });

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["compras", appliedFilters, page, pageSize],
    queryFn: () =>
      fetchCompras({
        proveedor: appliedFilters.proveedor || undefined,
        numeroDocumento: appliedFilters.numeroDocumento || undefined,
        fechaDesde: appliedFilters.fechaDesde || undefined,
        fechaHasta: appliedFilters.fechaHasta || undefined,
        page,
        pageSize,
      }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setAppliedFilters({ proveedor, numeroDocumento, fechaDesde, fechaHasta });
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;

  return (
    <div className="space-y-6">
      <form
        onSubmit={handleSubmit}
        className="grid grid-cols-1 gap-4 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <label className="flex flex-col gap-1 text-sm">
          Proveedor
          <input
            className="rounded border border-slate-300 px-2 py-1"
            value={proveedor}
            onChange={(e) => setProveedor(e.target.value)}
            placeholder="Razón social"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Nro. documento
          <input
            className="rounded border border-slate-300 px-2 py-1"
            value={numeroDocumento}
            onChange={(e) => setNumeroDocumento(e.target.value)}
            placeholder="0001-00012345"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Fecha desde
          <input
            type="date"
            className="rounded border border-slate-300 px-2 py-1"
            value={fechaDesde}
            onChange={(e) => setFechaDesde(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Fecha hasta
          <input
            type="date"
            className="rounded border border-slate-300 px-2 py-1"
            value={fechaHasta}
            onChange={(e) => setFechaHasta(e.target.value)}
          />
        </label>
        <div className="sm:col-span-2 lg:col-span-4">
          <button
            type="submit"
            className="rounded bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700"
          >
            Buscar
          </button>
        </div>
      </form>

      {isLoading && <p className="text-slate-600">Cargando…</p>}

      {isError && (
        <p className="text-red-700">
          Ocurrió un error al buscar compras: {(error as Error)?.message}
        </p>
      )}

      {data && data.items.length === 0 && (
        <p className="rounded border border-slate-200 bg-white p-6 text-center text-slate-600">
          Sin resultados para esta búsqueda.
        </p>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-100 text-left">
                <tr>
                  <th className="px-3 py-2">Fecha</th>
                  <th className="px-3 py-2">Proveedor</th>
                  <th className="px-3 py-2">Tipo documento</th>
                  <th className="px-3 py-2">Nro. documento</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((compra) => (
                  <tr key={compra.idCompra} className="hover:bg-slate-50">
                    <td className="px-3 py-2">
                      <Link
                        className="text-blue-700 underline"
                        href={`/compras/${compra.idCompra}`}
                      >
                        {compra.fecha ?? "—"}
                      </Link>
                    </td>
                    <td className="px-3 py-2">
                      {compra.proveedor?.razonSocial ?? "—"}
                    </td>
                    <td className="px-3 py-2">{compra.tipoDocumento ?? "—"}</td>
                    <td className="px-3 py-2">{compra.numeroDocumento ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between text-sm text-slate-600">
            <span>
              Página {data.page} de {totalPages} — {data.total} compras
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
