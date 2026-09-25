"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  fetchDetalleConciliacion,
  fetchResumenConciliacion,
  type ResumenContacto,
} from "@/services/conciliacionHistoricaApi";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { formatCantidad } from "@/lib/format";

const SUBCATEGORIA_LABEL: Record<string, string> = {
  "sin-contacto": "Sin contacto identificable",
  "sin-documento-comercial": "Nunca tuvo compra/venta cargada",
  "con-documento-sin-pendiente": "Tiene documentos, sin saldo pendiente que cubra el pago",
};

function columnas(onVerDetalle: (idContacto: number) => void): DataTableColumn<ResumenContacto>[] {
  return [
    {
      key: "razonSocial",
      header: "Contacto",
      sortValue: (r) => r.razonSocial ?? "",
      render: (r) => (
        <button type="button" className="text-finance underline" onClick={() => onVerDetalle(r.idContacto)}>
          {r.razonSocial ?? `Contacto #${r.idContacto}`}
        </button>
      ),
    },
    {
      key: "aplicadosExactos",
      header: "Exactos",
      align: "right",
      numeric: true,
      sortValue: (r) => r.aplicadosExactos,
      render: (r) => formatCantidad(r.aplicadosExactos),
    },
    {
      key: "aplicadosMejorEsfuerzo",
      header: "Mejor esfuerzo",
      align: "right",
      numeric: true,
      sortValue: (r) => r.aplicadosMejorEsfuerzo,
      render: (r) => (
        <span className={r.aplicadosMejorEsfuerzo > 0 ? "text-status-warning" : undefined}>
          {formatCantidad(r.aplicadosMejorEsfuerzo)}
        </span>
      ),
    },
    {
      key: "revisionManual",
      header: "Revisión manual",
      align: "right",
      numeric: true,
      sortValue: (r) => r.revisionManual,
      render: (r) => (
        <span className={r.revisionManual > 0 ? "text-status-danger font-medium" : undefined}>
          {formatCantidad(r.revisionManual)}
        </span>
      ),
    },
    {
      key: "fueraDeAlcance",
      header: "Fuera de alcance",
      align: "right",
      numeric: true,
      sortValue: (r) => r.fueraDeAlcance,
      render: (r) => <span className="text-ink-secondary">{formatCantidad(r.fueraDeAlcance)}</span>,
    },
  ];
}

/** Revisión de la conciliación histórica (020, US2): qué se aplicó
 * automático, qué quedó como "mejor esfuerzo" y qué necesita mirada
 * humana, contacto por contacto. Lee de `ConciliacionHistoricoLog` — no
 * reprocesa el histórico en cada consulta (research.md §6). */
export function ConciliacionHistorica() {
  const [soloConDudas, setSoloConDudas] = useState(true);
  const [idContactoAbierto, setIdContactoAbierto] = useState<number | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["conciliacion-historico-resumen", soloConDudas],
    queryFn: () => fetchResumenConciliacion(soloConDudas),
  });

  return (
    <div className="space-y-4">
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={soloConDudas}
          onChange={(e) => setSoloConDudas(e.target.checked)}
          className="h-4 w-4"
        />
        Mostrar solo contactos con mejor esfuerzo o revisión manual pendiente
      </label>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al obtener el resumen." onRetry={() => refetch()} />}

      {data && data.contactos.length === 0 && (
        <EmptyState message="No hay contactos con casos pendientes de revisar." />
      )}

      {data && data.contactos.length > 0 && (
        <DataTable
          columns={columnas(setIdContactoAbierto)}
          rows={data.contactos}
          keyField={(r) => r.idContacto}
          emptyMessage="No hay contactos que mostrar."
          page={1}
          pageSize={Math.max(data.contactos.length, 1)}
          total={data.contactos.length}
          onPageChange={() => {}}
        />
      )}

      {idContactoAbierto != null && (
        <DetalleContactoPanel idContacto={idContactoAbierto} onCerrar={() => setIdContactoAbierto(null)} />
      )}
    </div>
  );
}

function DetalleContactoPanel({ idContacto, onCerrar }: { idContacto: number; onCerrar: () => void }) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["conciliacion-historico-detalle", idContacto],
    queryFn: () => fetchDetalleConciliacion(idContacto),
  });

  return (
    <div className="rounded-md border border-border p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-medium">Detalle del contacto #{idContacto}</h2>
        <button type="button" onClick={onCerrar} className="text-sm underline">
          Cerrar
        </button>
      </div>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al obtener el detalle." onRetry={() => refetch()} />}

      {data && (
        <div className="mt-3 space-y-4 text-sm">
          <div>
            <h3 className="font-medium text-ink-secondary">
              Aplicaciones automáticas ({data.aplicaciones.length})
            </h3>
            {data.aplicaciones.length === 0 ? (
              <p className="text-ink-secondary">Sin aplicaciones automáticas para este contacto.</p>
            ) : (
              <ul className="mt-1 space-y-1">
                {data.aplicaciones.map((a) => (
                  <li key={a.idAplicacion} className="flex flex-col border-b border-border py-1 last:border-0">
                    <span>
                      {a.origen === "automatica-mejor-esfuerzo" && (
                        <span className="mr-1 rounded bg-status-warning/20 px-1 text-xs text-status-warning">
                          mejor esfuerzo
                        </span>
                      )}
                      {a.origenMovimiento} #{a.idMovimientoOrigen} → {a.tipoDocumento} #{a.idDocumentoAplicado}
                    </span>
                    {a.notaConciliacion && <span className="text-xs text-ink-secondary">{a.notaConciliacion}</span>}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <h3 className="font-medium text-ink-secondary">Excepciones ({data.excepciones.length})</h3>
            {data.excepciones.length === 0 ? (
              <p className="text-ink-secondary">Sin excepciones para este contacto.</p>
            ) : (
              <ul className="mt-1 space-y-1">
                {data.excepciones.map((e) => (
                  <li key={`${e.origenMovimiento}-${e.idMovimientoOrigen}`} className="border-b border-border py-1 last:border-0">
                    {e.origenMovimiento} #{e.idMovimientoOrigen} —{" "}
                    <span className="text-ink-secondary">
                      {SUBCATEGORIA_LABEL[e.subcategoria] ?? e.subcategoria}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
