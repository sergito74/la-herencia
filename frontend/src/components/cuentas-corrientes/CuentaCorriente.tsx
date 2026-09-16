"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  fetchContactos,
  fetchMovimientos,
  fetchSaldo,
  type Contacto,
} from "@/services/cuentasCorrientesApi";
import { OrigenMovimiento } from "@/components/cuentas-corrientes/OrigenMovimiento";

// Valores confirmados de `Tipo Contacto` contra datos reales (data-model.md).
const TIPOS_CONTACTO = [
  "Banco",
  "Comprador",
  "Consignatario",
  "Empleado",
  "Multiple",
  "Organismo",
  "Proveedor",
  "Tarjeta de Credito",
];

/**
 * Búsqueda de contacto + saldo + movimientos (US1: FR-001, FR-002, FR-003,
 * FR-004, FR-005, FR-012, FR-013; US3: filtro por tipo, FR-002). Read-only:
 * no hay affordance de crear/editar/eliminar (FR-010).
 */
export function CuentaCorriente() {
  const [q, setQ] = useState("");
  const [tipoContacto, setTipoContacto] = useState("");
  const [appliedQ, setAppliedQ] = useState("");
  const [appliedTipoContacto, setAppliedTipoContacto] = useState("");
  const [selected, setSelected] = useState<Contacto | null>(null);
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [appliedDates, setAppliedDates] = useState({ fechaDesde: "", fechaHasta: "" });
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const {
    data: contactosData,
    isLoading: loadingContactos,
    isError: errorContactos,
  } = useQuery({
    queryKey: ["cc-contactos", appliedQ, appliedTipoContacto],
    queryFn: () =>
      fetchContactos({
        q: appliedQ || undefined,
        tipoContacto: appliedTipoContacto || undefined,
      }),
    enabled: appliedQ.length > 0 || appliedTipoContacto.length > 0,
  });

  const { data: saldo, isLoading: loadingSaldo } = useQuery({
    queryKey: ["cc-saldo", selected?.idContacto],
    queryFn: () => fetchSaldo(selected!.idContacto),
    enabled: selected !== null,
  });

  const {
    data: movimientos,
    isLoading: loadingMovimientos,
    isError: errorMovimientos,
    error: movimientosError,
  } = useQuery({
    queryKey: ["cc-movimientos", selected?.idContacto, appliedDates, page, pageSize],
    queryFn: () =>
      fetchMovimientos(selected!.idContacto, {
        fechaDesde: appliedDates.fechaDesde || undefined,
        fechaHasta: appliedDates.fechaHasta || undefined,
        page,
        pageSize,
      }),
    enabled: selected !== null,
  });

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setAppliedQ(q);
    setAppliedTipoContacto(tipoContacto);
    setSelected(null);
  }

  function handleSelectContacto(contacto: Contacto) {
    setSelected(contacto);
    setPage(1);
    setAppliedDates({ fechaDesde: "", fechaHasta: "" });
    setFechaDesde("");
    setFechaHasta("");
  }

  function handleDateFilterSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setAppliedDates({ fechaDesde, fechaHasta });
  }

  const totalPages = movimientos
    ? Math.max(1, Math.ceil(movimientos.total / movimientos.pageSize))
    : 1;

  return (
    <div className="space-y-6">
      <form
        onSubmit={handleSearchSubmit}
        className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-white p-4 sm:flex-row sm:items-end"
      >
        <label className="flex flex-1 flex-col gap-1 text-sm">
          Contacto
          <input
            className="rounded border border-slate-300 px-2 py-1"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Razón social"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm sm:w-48">
          Tipo de contacto
          <select
            className="rounded border border-slate-300 px-2 py-1"
            value={tipoContacto}
            onChange={(e) => setTipoContacto(e.target.value)}
          >
            <option value="">Todos</option>
            {TIPOS_CONTACTO.map((tipo) => (
              <option key={tipo} value={tipo}>
                {tipo}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          className="rounded bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700"
        >
          Buscar
        </button>
      </form>

      {loadingContactos && <p className="text-slate-600">Buscando…</p>}
      {errorContactos && (
        <p className="text-red-700">Ocurrió un error al buscar contactos.</p>
      )}

      {contactosData && !selected && (
        <>
          {contactosData.items.length === 0 && (
            <p className="rounded border border-slate-200 bg-white p-6 text-center text-slate-600">
              Sin resultados para esta búsqueda.
            </p>
          )}
          {contactosData.items.length > 0 && (
            <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white">
              {contactosData.items.map((contacto) => (
                <li key={contacto.idContacto}>
                  <button
                    type="button"
                    className="w-full px-4 py-2 text-left text-sm hover:bg-slate-50"
                    onClick={() => handleSelectContacto(contacto)}
                  >
                    {contacto.razonSocial ?? "—"}{" "}
                    <span className="text-slate-500">
                      ({contacto.tipoContacto ?? "sin tipo"})
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      {selected && (
        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4">
            <div>
              <h2 className="text-lg font-semibold">
                {selected.razonSocial ?? "—"}
              </h2>
              <p className="text-sm text-slate-600">
                {selected.tipoContacto ?? "sin tipo"}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-slate-600">Saldo</p>
              <p className="text-xl font-semibold">
                {loadingSaldo
                  ? "…"
                  : saldo?.saldoParcial != null
                    ? saldo.saldoParcial.toLocaleString("es-AR", {
                        style: "currency",
                        currency: "ARS",
                      })
                    : "—"}
              </p>
            </div>
            <button
              type="button"
              className="text-sm text-blue-700 underline"
              onClick={() => setSelected(null)}
            >
              Cambiar contacto
            </button>
          </div>

          <form
            onSubmit={handleDateFilterSubmit}
            className="grid grid-cols-1 gap-4 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-3"
          >
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
            <div className="flex items-end">
              <button
                type="submit"
                className="rounded bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700"
              >
                Filtrar
              </button>
            </div>
          </form>

          {loadingMovimientos && <p className="text-slate-600">Cargando…</p>}
          {errorMovimientos && (
            <p className="text-red-700">
              Ocurrió un error al obtener movimientos:{" "}
              {(movimientosError as Error)?.message}
            </p>
          )}

          {movimientos && movimientos.items.length === 0 && (
            <p className="rounded border border-slate-200 bg-white p-6 text-center text-slate-600">
              Sin movimientos para el período seleccionado.
            </p>
          )}

          {movimientos && movimientos.items.length > 0 && (
            <>
              <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-100 text-left">
                    <tr>
                      <th className="px-3 py-2">Fecha</th>
                      <th className="px-3 py-2">Documento</th>
                      <th className="px-3 py-2">Nro. documento</th>
                      <th className="px-3 py-2 text-right">Deuda (débito)</th>
                      <th className="px-3 py-2 text-right">Crédito (haber)</th>
                      <th className="px-3 py-2">Origen</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {movimientos.items.map((mov, idx) => (
                      <tr key={idx} className="hover:bg-slate-50">
                        <td className="px-3 py-2">{mov.fecha ?? "—"}</td>
                        <td className="px-3 py-2">{mov.documento ?? "—"}</td>
                        <td className="px-3 py-2">{mov.numeroDocumento ?? "—"}</td>
                        <td className="px-3 py-2 text-right text-red-700">
                          {mov.deuda ? mov.deuda.toLocaleString("es-AR") : "—"}
                        </td>
                        <td className="px-3 py-2 text-right text-green-700">
                          {mov.credito ? mov.credito.toLocaleString("es-AR") : "—"}
                        </td>
                        <td className="px-3 py-2 text-sm">
                          <OrigenMovimiento origen={mov.origen} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex items-center justify-between text-sm text-slate-600">
                <span>
                  Página {movimientos.page} de {totalPages} — {movimientos.total}{" "}
                  movimientos
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
      )}
    </div>
  );
}
