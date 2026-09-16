"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchArrendamientos } from "@/services/arrendamientosApi";
import { StatusBadge, type BadgeTone } from "@/components/ui/StatusBadge";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";

/**
 * Único valor de `Estado` confirmado contra datos reales hoy: "Cobrado".
 * Cualquier otro valor (o vacío) se trata como pendiente, y se resalta
 * como vencido si su fecha de vencimiento ya pasó — no se asume un enum
 * cerrado que los datos no respaldan (design/agroux-frontend-redesign.md §4.2).
 */
function estadoCuota(estado: string | null, fechaVencimiento: string | null): { label: string; tone: BadgeTone } {
  if (estado && estado.toLowerCase() === "cobrado") return { label: "Cobrado", tone: "success" };
  const hoy = new Date().toISOString().slice(0, 10);
  if (fechaVencimiento && fechaVencimiento < hoy) return { label: "Vencido", tone: "danger" };
  return { label: estado ?? "Pendiente", tone: "warning" };
}

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
      <FilterBar onSubmit={handleSubmit}>
        <FilterField label="Contacto">
          <input
            className={filterInputClass}
            value={contacto}
            onChange={(e) => setContacto(e.target.value)}
            placeholder="Razón social"
          />
        </FilterField>
        <FilterSubmitButton />
      </FilterBar>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al buscar arrendamientos." />}

      {data && data.items.length === 0 && (
        <EmptyState message="Sin resultados para esta búsqueda." />
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="space-y-4">
            {data.items.map((a) => {
              const cobradas = a.cobros.filter((c) => c.estado?.toLowerCase() === "cobrado").length;
              return (
                <div key={a.idAlquiler} className="rounded-md border border-border bg-surface p-4">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <div>
                      <h3 className="font-semibold text-ink-primary">
                        Arrendamiento — {a.contacto ?? "—"}
                      </h3>
                      <p className="text-sm text-ink-secondary">
                        {a.inicioPeriodo ?? "—"} a {a.finPeriodo ?? "—"}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-data text-sm text-ink-secondary">
                        Importe total del contrato:{" "}
                        <span className="font-medium text-ink-primary">
                          {a.importeTotalContrato != null
                            ? a.importeTotalContrato.toLocaleString("es-AR")
                            : "—"}
                        </span>
                      </p>
                      {a.cantidadCuotas != null && a.cantidadCuotas > 0 && (
                        <p className="text-xs text-ink-secondary">
                          {cobradas} de {a.cantidadCuotas} cuotas cobradas
                        </p>
                      )}
                    </div>
                  </div>

                  {a.cobros.length === 0 ? (
                    <EmptyState message="Sin cobros registrados todavía." />
                  ) : (
                    <table className="mt-3 min-w-full divide-y divide-border text-sm">
                      <thead className="text-left text-ink-secondary">
                        <tr>
                          <th className="px-2 py-1">Cuota</th>
                          <th className="px-2 py-1">Vencimiento</th>
                          <th className="px-2 py-1">Estado</th>
                          <th className="px-2 py-1 text-right">Importe</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {a.cobros.map((c) => {
                          const estado = estadoCuota(c.estado, c.fechaVencimiento);
                          return (
                            <tr key={c.idCobroAlquiler}>
                              <td className="px-2 py-1 font-data">{c.numeroCuota ?? "—"}</td>
                              <td className="px-2 py-1 font-data">{c.fechaVencimiento ?? "—"}</td>
                              <td className="px-2 py-1">
                                <StatusBadge label={estado.label} tone={estado.tone} />
                              </td>
                              <td className="px-2 py-1 text-right font-data">
                                {c.importeCuota != null ? c.importeCuota.toLocaleString("es-AR") : "—"}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  )}
                </div>
              );
            })}
          </div>

          <div className="flex items-center justify-between text-sm text-ink-secondary">
            <span>
              Página {data.page} de {totalPages} — {data.total} arrendamientos
            </span>
            <div className="flex gap-2">
              <button
                className="rounded-sm border border-border px-3 py-1 disabled:opacity-40"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Anterior
              </button>
              <button
                className="rounded-sm border border-border px-3 py-1 disabled:opacity-40"
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
