"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { actualizarEstadoCuota, fetchArrendamientos } from "@/services/arrendamientosApi";
import { ContactoLink } from "@/components/ui/ContactoLink";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { StatusBadge, type BadgeTone } from "@/components/ui/StatusBadge";
import { FilterBar, FilterSubmitButton } from "@/components/ui/FilterBar";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
import { formatMoneda, formatCantidad } from "@/lib/format";

/**
 * Enum real confirmado en el formulario Access (`Subformulario Detalle
 * Cobro Alquiler`, combo `Estado`): solo "Pendiente"/"Cobrado". "Vencido"
 * es una capa de presentación propia (no un valor almacenado): se resalta
 * cuando una cuota "Pendiente" ya pasó su fecha de vencimiento.
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
 *
 * Desde 2026-09-17 permite marcar una cuota como Cobrada/Pendiente
 * (primera acción de escritura real de la app) — escribe exclusivamente
 * contra `WC`, nunca contra `LaHerencia` (regla de oro, ver memory.md).
 */
export function ArrendamientosListado() {
  const searchParams = useSearchParams();
  const highlight = searchParams.get("highlight");
  const highlightId = highlight ? Number(highlight) : null;
  const highlightRef = useRef<HTMLDivElement | null>(null);
  const [contacto, setContacto] = useState<{ id: number | null; nombre: string | null }>({
    id: null,
    nombre: null,
  });
  const [appliedContacto, setAppliedContacto] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const queryKey = ["arrendamientos", appliedContacto, page];
  const { data, isLoading, isError } = useQuery({
    queryKey,
    queryFn: () =>
      fetchArrendamientos({ contacto: appliedContacto || undefined, page, pageSize }),
  });

  const toggleEstadoMutation = useMutation({
    mutationFn: ({ idCobroAlquiler, estado }: { idCobroAlquiler: number; estado: "Pendiente" | "Cobrado" }) =>
      actualizarEstadoCuota(idCobroAlquiler, estado),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey });
      showToast(
        variables.estado === "Cobrado" ? "Cuota marcada como cobrada." : "Cuota marcada como pendiente.",
        "success",
      );
    },
    onError: () => {
      showToast("No se pudo actualizar el estado de la cuota. Intentá de nuevo.", "danger");
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setAppliedContacto(contacto.nombre ?? "");
  }

  useEffect(() => {
    if (highlightId != null && highlightRef.current) {
      highlightRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlightId, data]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;

  return (
    <div className="space-y-4">
      <FilterBar onSubmit={handleSubmit}>
        <ContactoSelect
          label="Contacto"
          value={contacto.id}
          razonSocial={contacto.nombre}
          onChange={(id, nombre) => setContacto({ id, nombre })}
          placeholder="Buscar arrendatario…"
        />
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
              const isHighlighted = highlightId != null && a.idAlquiler === highlightId;
              return (
                <div
                  key={a.idAlquiler}
                  ref={isHighlighted ? highlightRef : undefined}
                  className={`rounded-md border p-4 ${
                    isHighlighted ? "border-status-warning bg-status-warning-bg" : "border-border bg-surface"
                  }`}
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <div>
                      <h3 className="font-semibold text-ink-primary">
                        Arrendamiento —{" "}
                        <ContactoLink idContacto={a.idContacto} razonSocial={a.contacto} />
                      </h3>
                      <p className="text-xs text-ink-muted">Arrendatario</p>
                      <p className="mt-1 text-sm text-ink-secondary">
                        {a.inicioPeriodo ?? "—"} a {a.finPeriodo ?? "—"}
                        {a.tipoDePago ? ` · ${a.tipoDePago}` : ""}
                        {a.superficieTotal != null ? ` · ${formatCantidad(a.superficieTotal)} ha` : ""}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-data text-sm text-ink-secondary">
                        Importe total del contrato:{" "}
                        <span className="font-medium text-ink-primary">
                          {a.importeTotalContrato != null
                            ? formatMoneda(a.importeTotalContrato)
                            : "—"}
                        </span>
                      </p>
                      {a.retencionGanancias != null && a.retencionGanancias !== 0 && (
                        <p className="font-data text-xs text-ink-secondary">
                          Ret. Ganancias: {formatMoneda(a.retencionGanancias)}
                        </p>
                      )}
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
                          <th className="px-2 py-1" />
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {a.cobros.map((c) => {
                          const estado = estadoCuota(c.estado, c.fechaVencimiento);
                          const yaCobrada = c.estado?.toLowerCase() === "cobrado";
                          const isPending =
                            toggleEstadoMutation.isPending &&
                            toggleEstadoMutation.variables?.idCobroAlquiler === c.idCobroAlquiler;
                          return (
                            <tr key={c.idCobroAlquiler}>
                              <td className="px-2 py-1 font-data">{c.numeroCuota ?? "—"}</td>
                              <td className="px-2 py-1 font-data">{c.fechaVencimiento ?? "—"}</td>
                              <td className="px-2 py-1">
                                <StatusBadge label={estado.label} tone={estado.tone} />
                              </td>
                              <td className="px-2 py-1 text-right font-data">
                                {c.importeCuota != null ? formatMoneda(c.importeCuota) : "—"}
                              </td>
                              <td className="px-2 py-1 text-right">
                                <button
                                  type="button"
                                  disabled={isPending}
                                  className="rounded-sm border border-border px-2 py-0.5 text-xs text-ink-secondary hover:border-border-strong hover:text-ink-primary disabled:opacity-40"
                                  onClick={() =>
                                    toggleEstadoMutation.mutate({
                                      idCobroAlquiler: c.idCobroAlquiler,
                                      estado: yaCobrada ? "Pendiente" : "Cobrado",
                                    })
                                  }
                                >
                                  {isPending
                                    ? "Guardando…"
                                    : yaCobrada
                                      ? "Marcar pendiente"
                                      : "Marcar cobrada"}
                                </button>
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
