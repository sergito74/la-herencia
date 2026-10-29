"use client";

import Link from "next/link";
import { AdicionalSierra } from "@/components/remuneraciones/AdicionalSierra";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchRemuneraciones, subirRecibo, urlRecibo, type Remuneracion } from "@/services/remuneracionesApi";
import { ApiError } from "@/services/apiClient";
import { urlDocumentoLocal } from "@/services/comprasApi";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { ContactoLink } from "@/components/ui/ContactoLink";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterSubmitButton } from "@/components/ui/FilterBar";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
import { formatMoneda, formatFecha } from "@/lib/format";
import { LiquidacionForm } from "@/components/remuneraciones/NuevaLiquidacionForm";
import {
  BASE_DOCUMENTOS_RECIBOS,
  esReciboAusente,
  normalizarDocumentoOriginal,
} from "@/lib/documentoLocal";

function urlDelRecibo(r: Remuneracion): string {
  if (!esReciboAusente(r.recibo)) {
    return urlDocumentoLocal(normalizarDocumentoOriginal(r.recibo as string, BASE_DOCUMENTOS_RECIBOS));
  }
  return urlRecibo(r.idSalario);
}

function AdjuntarReciboAccion({ idSalario, onSubido }: { idSalario: number; onSubido: () => Promise<void> | void }) {
  const { showToast } = useToast();
  const [subiendo, setSubiendo] = useState(false);

  async function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const archivo = e.target.files?.[0];
    e.target.value = "";
    if (!archivo) return;
    setSubiendo(true);
    try {
      await subirRecibo(idSalario, archivo);
      showToast("Recibo subido.", "success");
      await onSubido();
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : "Error al subir el recibo.", "danger");
    } finally {
      setSubiendo(false);
    }
  }

  return (
    <label className="cursor-pointer text-finance underline">
      {subiendo ? "Subiendo…" : "Adjuntar/reemplazar"}
      <input type="file" accept="application/pdf" className="hidden" disabled={subiendo} onChange={handleChange} />
    </label>
  );
}

function buildColumns(
  onReciboSubido: () => Promise<void> | void,
  onEditar: (idSalario: number) => void
): DataTableColumn<Remuneracion>[] {
  return [
    {
      key: "acciones",
      header: "Acción",
      render: (r) => (
        <button
          type="button"
          onClick={() => onEditar(r.idSalario)}
          className="rounded border border-border bg-surface px-2.5 py-1 text-xs font-medium text-finance hover:bg-surface-sunken"
        >
          Ver / Editar
        </button>
      ),
    },
    {
      key: "adicional",
      header: "Adicional fuera de recibo",
      render: (r) =>
        r.idContacto === 374 && !r.periodoLiquidado?.toLowerCase().startsWith("adicional fuera de recibo") ? (
          <AdicionalSierra idSalario={r.idSalario} fechaSugerida={r.fechaPago ?? undefined} />
        ) : (
          "—"
        ),
    },
    {
      key: "trabajos",
      header: "Trabajos",
      render: (r) => (
        <Link
          className="text-finance underline"
          href={`/personal/trabajos-eventuales?idContacto=${r.idContacto ?? ""}&empleado=${encodeURIComponent(r.empleado ?? "")}&idSalario=${r.idSalario}`}
        >
          Ver / vincular
        </Link>
      ),
    },
    {
      key: "fechaPago",
      header: "Fecha de pago",
      numeric: true,
      sortValue: (r) => r.fechaPago,
      render: (r) => formatFecha(r.fechaPago),
    },
    { key: "periodoLiquidado", header: "Período", render: (r) => r.periodoLiquidado ?? "—" },
    {
      key: "empleado",
      header: "Empleado",
      sortValue: (r) => r.empleado,
      render: (r) =>
        r.idContacto != null ? (
          <ContactoLink idContacto={r.idContacto} razonSocial={r.empleado} tipoContacto="Empleado" />
        ) : (
          <span className="italic text-ink-muted">Contacto no disponible</span>
        ),
    },
    {
      key: "importe",
      header: "Importe liquidado (calculado)",
      align: "right",
      numeric: true,
      sortValue: (r) => r.importe,
      render: (r) => (r.importe != null ? formatMoneda(r.importe) : "—"),
    },
    {
      key: "recibo",
      header: "Recibo",
      render: (r) => (
        <div className="flex items-center gap-3">
          <a href={urlDelRecibo(r)} target="_blank" rel="noopener noreferrer" className="text-finance underline">
            Ver
          </a>
          <SoloLectura>
            <AdjuntarReciboAccion idSalario={r.idSalario} onSubido={onReciboSubido} />
          </SoloLectura>
        </div>
      ),
    },
  ];
}

export function RemuneracionesListado({
  highlightKey,
  empleadoInicial,
}: {
  highlightKey?: number;
  empleadoInicial?: string | null;
}) {
  const [empleado, setEmpleado] = useState<{ id: number | null; nombre: string | null }>({
    id: null,
    nombre: empleadoInicial ?? null,
  });
  const [appliedEmpleado, setAppliedEmpleado] = useState(empleadoInicial ?? "");
  const [page, setPage] = useState(1);
  const [mostrarAlta, setMostrarAlta] = useState(false);
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const pageSize = 50;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["remuneraciones", appliedEmpleado, page],
    queryFn: () => fetchRemuneraciones({ empleado: appliedEmpleado, page, pageSize }),
    enabled: appliedEmpleado !== "",
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setAppliedEmpleado(empleado.nombre ?? "");
  }

  return (
    <div className="space-y-4">
      <FilterBar onSubmit={handleSubmit}>
        <ContactoSelect
          label="Empleado"
          tipoContacto="Empleado"
          value={empleado.id}
          razonSocial={empleado.nombre}
          onChange={(id, nombre) => setEmpleado({ id, nombre })}
          placeholder="Buscar empleado…"
        />
        <FilterSubmitButton />
      </FilterBar>

      <div className="flex items-center gap-3">
        <SoloLectura>
          <button
            type="button"
            onClick={() => {
              setEditandoId(null);
              setMostrarAlta((v) => !v);
            }}
            className="rounded border border-border px-3 py-1.5 text-sm font-medium hover:bg-surface-sunken"
          >
            {mostrarAlta ? "Cancelar alta" : "Nueva liquidación…"}
          </button>
        </SoloLectura>
      </div>

      {mostrarAlta && (
        <LiquidacionForm
          onGuardada={async () => {
            setMostrarAlta(false);
            if (appliedEmpleado !== "") await refetch();
          }}
          onCancelar={() => setMostrarAlta(false)}
        />
      )}

      {editandoId && (
        <LiquidacionForm
          idSalario={editandoId}
          onGuardada={async () => {
            setEditandoId(null);
            await refetch();
          }}
          onCancelar={() => setEditandoId(null)}
        />
      )}

      {appliedEmpleado === "" && (
        <EmptyState message="Elegí un empleado para ver sus liquidaciones." />
      )}
      {appliedEmpleado !== "" && isLoading && <LoadingState />}
      {appliedEmpleado !== "" && isError && (
        <ErrorState message="Ocurrió un error al buscar liquidaciones." onRetry={() => refetch()} />
      )}

      {appliedEmpleado !== "" && data && (
        <DataTable
          columns={buildColumns(
            async () => {
              await refetch();
            },
            (id) => {
              setMostrarAlta(false);
              setEditandoId(id);
              window.scrollTo({ top: 0, behavior: "smooth" });
            }
          )}
          rows={data.items}
          keyField={(r) => r.idSalario}
          emptyMessage="Sin resultados para esta búsqueda."
          page={data.page}
          pageSize={data.pageSize}
          total={data.total}
          onPageChange={setPage}
          highlightKey={highlightKey}
        />
      )}
    </div>
  );
}
