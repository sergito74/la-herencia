"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  descartarCandidato,
  fetchCandidatos,
  reasignarMovimiento,
  type Candidato,
} from "@/services/reasignacionContactoApi";
import { ApiError } from "@/services/apiClient";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
import { formatMoneda } from "@/lib/format";

/** Detección de candidatos a reasignación (022, US2): solo lectura hasta
 * que el usuario confirma (FR-009) — "Reasignar" reutiliza el mismo
 * endpoint de US1 con el contacto sugerido pre-cargado, "Descartar" solo
 * registra el falso positivo (FR-010), sin aplicar ningún cambio. */
export function CandidatosReasignacion() {
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [procesando, setProcesando] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["reasignacion-candidatos"],
    queryFn: fetchCandidatos,
  });

  function clave(c: Candidato) {
    return `${c.origen}-${c.idOrigen}-${c.idContactoSugerido}`;
  }

  async function confirmar(c: Candidato) {
    setProcesando(clave(c));
    try {
      await reasignarMovimiento(c.origen, c.idOrigen, c.idContactoSugerido);
      showToast(`Reasignado a ${c.contactoSugerido ?? c.idContactoSugerido}.`, "success");
      await refetch();
      queryClient.invalidateQueries({ queryKey: ["cc-saldos"] });
      queryClient.invalidateQueries({ queryKey: ["cc-movimientos"] });
      queryClient.invalidateQueries({ queryKey: ["cc-saldo"] });
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "Error al reasignar.", "danger");
    } finally {
      setProcesando(null);
    }
  }

  async function descartar(c: Candidato) {
    setProcesando(clave(c));
    try {
      await descartarCandidato(c.origen, c.idOrigen, c.idContactoSugerido);
      showToast("Candidato descartado.", "success");
      await refetch();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "Error al descartar.", "danger");
    } finally {
      setProcesando(null);
    }
  }

  const columns: DataTableColumn<Candidato>[] = [
    { key: "fecha", header: "Fecha", render: (c) => c.fecha?.slice(0, 10) ?? "—" },
    { key: "descripcion", header: "Descripción", render: (c) => c.descripcion ?? "—" },
    {
      key: "importe",
      header: "Importe",
      align: "right",
      numeric: true,
      render: (c) => formatMoneda(c.importe),
    },
    { key: "contactoActual", header: "Asignado hoy a", render: (c) => c.contactoActual ?? "—" },
    { key: "contactoSugerido", header: "¿Debería ser…?", render: (c) => c.contactoSugerido ?? "—" },
    {
      key: "acciones",
      header: "",
      render: (c) => (
        <SoloLectura>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={procesando === clave(c)}
              onClick={() => confirmar(c)}
              className="rounded bg-finance px-2 py-1 text-xs text-white disabled:opacity-50"
            >
              Reasignar
            </button>
            <button
              type="button"
              disabled={procesando === clave(c)}
              onClick={() => descartar(c)}
              className="rounded border border-border px-2 py-1 text-xs hover:bg-surface-sunken disabled:opacity-50"
            >
              Descartar
            </button>
          </div>
        </SoloLectura>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al ejecutar la detección." onRetry={() => refetch()} />}

      {data && (
        <DataTable
          columns={columns}
          rows={data.candidatos}
          keyField={clave}
          emptyMessage="Sin candidatos pendientes de revisión."
          page={1}
          pageSize={Math.max(data.candidatos.length, 1)}
          total={data.candidatos.length}
          onPageChange={() => {}}
        />
      )}
    </div>
  );
}
