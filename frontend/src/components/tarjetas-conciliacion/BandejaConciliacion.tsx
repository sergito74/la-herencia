"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  aceptarExactas,
  fetchExactasPropuestas,
  fetchPendientes,
  type FiltrosPendientes,
  type LineaPendiente,
} from "@/services/tarjetasResumenesApi";
import { fetchTarjetas } from "@/services/tarjetasApi";
import { formatCantidad, formatMoneda } from "@/lib/format";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
import { PanelConciliacion } from "@/components/tarjetas-conciliacion/PanelConciliacion";
import { BotonExportarConciliacion } from "@/components/tarjetas-conciliacion/BotonExportarConciliacion";

const PAGE_SIZE = 25;

const nombreDoc = (d: { tipoDocumento: string | null; numeroDocumento: string | null }) =>
  `${d.tipoDocumento ?? "Documento"} ${d.numeroDocumento ?? ""}`.trim();

interface FiltrosForm {
  idTarjeta: string;
  proveedor: string;
  fechaCierreDesde: string;
  fechaCierreHasta: string;
  soloConSugerencia: boolean;
}

const FILTROS_VACIOS: FiltrosForm = {
  idTarjeta: "",
  proveedor: "",
  fechaCierreDesde: "",
  fechaCierreHasta: "",
  soloConSugerencia: false,
};

/** Modal de vista previa de "Aceptar sugerencias exactas": lista lo que se va a
 * vincular y recién al confirmar se aplica. */
function ModalExactas({ onClose, onApplied }: { onClose: () => void; onApplied: () => void }) {
  const { showToast } = useToast();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["conciliacion-exactas"],
    queryFn: fetchExactasPropuestas,
    staleTime: 0,
    gcTime: 0,
  });
  const [excluidas, setExcluidas] = useState<number[]>([]);

  const aplicar = useMutation({
    mutationFn: (ids: number[]) => aceptarExactas(ids),
    onSuccess: (r) => {
      showToast(
        r.omitidas.length ? `${r.aplicadas} vinculadas, ${r.omitidas.length} omitidas.` : `${r.aplicadas} líneas conciliadas.`,
        "success"
      );
      onApplied();
    },
    onError: () => showToast("No se pudieron aplicar las sugerencias.", "danger"),
  });

  const elegidas = (data ?? []).filter((p) => !excluidas.includes(p.idLineaConsumo));

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-ink-primary/40 p-4">
      <div className="flex max-h-[85vh] w-full max-w-4xl flex-col rounded-md border border-border bg-surface shadow-lg">
        <div className="border-b border-border px-4 py-3">
          <h2 className="font-semibold">Aceptar sugerencias exactas</h2>
          <p className="text-xs text-ink-secondary">
            Solo combinaciones únicas, en pesos y sin documentos compartidos con otra línea. Revisá y destildá las que no quieras aplicar.
          </p>
        </div>
        <div className="flex-1 overflow-auto px-4 py-2">
          {isLoading && <LoadingState />}
          {isError && <p className="text-sm text-status-danger">No se pudo calcular la vista previa.</p>}
          {data && data.length === 0 && <EmptyState message="No hay sugerencias exactas seguras para aplicar en bloque." />}
          {data && data.length > 0 && (
            <table className="w-full text-xs">
              <thead className="text-left text-ink-secondary">
                <tr>
                  <th className="w-6" />
                  <th className="py-1 pr-2">Tarjeta · resumen</th>
                  <th className="pr-2">Fecha</th>
                  <th className="pr-2">Línea</th>
                  <th className="pr-2 text-right">Importe</th>
                  <th>Se vincula con</th>
                </tr>
              </thead>
              <tbody>
                {data.map((p) => (
                  <tr key={p.idLineaConsumo} className="border-t border-border align-top">
                    <td className="py-1">
                      <input
                        type="checkbox"
                        checked={!excluidas.includes(p.idLineaConsumo)}
                        onChange={() =>
                          setExcluidas((prev) => (prev.includes(p.idLineaConsumo) ? prev.filter((x) => x !== p.idLineaConsumo) : [...prev, p.idLineaConsumo]))
                        }
                        aria-label={`Aplicar línea ${p.idLineaConsumo}`}
                      />
                    </td>
                    <td className="py-1 pr-2">
                      {p.tarjeta} · {p.resumenCodigo}
                    </td>
                    <td className="pr-2 whitespace-nowrap">{p.fechaCompra?.slice(0, 10)}</td>
                    <td className="pr-2">
                      {p.proveedor ?? "—"} <span className="text-ink-secondary">{p.detalle}</span>
                    </td>
                    <td className="pr-2 text-right font-data whitespace-nowrap">{formatMoneda(p.importe)}</td>
                    <td>{p.documentos.map((d) => `${nombreDoc(d)} (${formatMoneda(d.importePesos)})`).join(" + ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-border px-4 py-3">
          <button type="button" onClick={onClose} className="rounded-sm border border-border px-3 py-1 text-sm text-ink-secondary hover:text-ink-primary">
            Cancelar
          </button>
          <button
            type="button"
            disabled={elegidas.length === 0 || aplicar.isPending}
            onClick={() => aplicar.mutate(elegidas.map((p) => p.idLineaConsumo))}
            className="rounded-sm bg-finance px-3 py-1 text-sm text-white hover:opacity-90 disabled:opacity-40"
          >
            {aplicar.isPending ? "Aplicando…" : `Aplicar ${elegidas.length}`}
          </button>
        </div>
      </div>
    </div>
  );
}

/** Bandeja de conciliación (009): líneas de consumo de todos los resúmenes que
 * todavía no tienen documentos vinculados ni resolución manual. */
export function BandejaConciliacion() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<FiltrosForm>(FILTROS_VACIOS);
  const [aplicados, setAplicados] = useState<FiltrosForm>(FILTROS_VACIOS);
  const [page, setPage] = useState(1);
  const [abierta, setAbierta] = useState<number | null>(null);
  const [verExactas, setVerExactas] = useState(false);

  const { data: tarjetas } = useQuery({ queryKey: ["tarjetas"], queryFn: () => fetchTarjetas(false), staleTime: Infinity });

  const filtros: FiltrosPendientes = {
    idTarjeta: aplicados.idTarjeta || undefined,
    proveedor: aplicados.proveedor || undefined,
    fechaCierreDesde: aplicados.fechaCierreDesde || undefined,
    fechaCierreHasta: aplicados.fechaCierreHasta || undefined,
    soloConSugerencia: aplicados.soloConSugerencia,
    page,
    pageSize: PAGE_SIZE,
  };
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["conciliacion-pendientes", filtros],
    queryFn: () => fetchPendientes(filtros),
    staleTime: 0,
  });

  function refrescar() {
    queryClient.invalidateQueries({ queryKey: ["conciliacion-pendientes"] });
    queryClient.invalidateQueries({ queryKey: ["tarjeta-movimientos"], refetchType: "all" });
    queryClient.invalidateQueries({ queryKey: ["tarjeta-resumen-detalle"], refetchType: "all" });
  }

  const columnas: DataTableColumn<LineaPendiente>[] = [
    {
      key: "resumen",
      header: "Tarjeta · resumen",
      render: (r) => (
        <span>
          {r.tarjeta ?? "—"} <span className="text-ink-secondary">· {r.resumenCodigo}</span>
          <span className="block text-xs text-ink-secondary">cierre {r.fechaCierre?.slice(0, 10) ?? "—"}</span>
        </span>
      ),
    },
    { key: "fecha", header: "Fecha", numeric: true, render: (r) => r.fechaCompra?.slice(0, 10) ?? "—" },
    {
      key: "detalle",
      header: "Proveedor / detalle",
      render: (r) => (
        <span>
          {r.proveedor ?? <span className="text-ink-secondary">Sin proveedor</span>}
          <span className="block text-xs text-ink-secondary">{r.detalle}</span>
        </span>
      ),
    },
    { key: "importe", header: "Importe", numeric: true, align: "right", render: (r) => formatMoneda(r.importe) },
    {
      key: "sugerencia",
      header: "Sugerencia",
      render: (r) =>
        r.sugerencia ? (
          <span className="text-xs">
            <span className="text-status-success">● </span>
            {r.sugerencia.documentos.map((d) => nombreDoc(d)).join(" + ")}
            {!r.sugerencia.unica && <span className="text-ink-secondary"> (hay más opciones)</span>}
          </span>
        ) : (
          <span className="text-xs text-ink-secondary">
            {r.cantidadDocumentos === 0 ? "Sin documentos del proveedor" : `${r.cantidadDocumentos} documentos, sin combinación exacta`}
          </span>
        ),
    },
    {
      key: "accion",
      header: "",
      render: (r) => (
        <button type="button" onClick={() => setAbierta(r.idLineaConsumo)} className="rounded-sm border border-finance px-2 py-0.5 text-xs text-finance hover:bg-finance-light">
          Conciliar
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-secondary">
          {data ? (
            <>
              <strong className="text-ink-primary">{formatCantidad(data.total)}</strong> líneas pendientes ·{" "}
              <strong className="text-ink-primary">{formatCantidad(data.totalConSugerencia)}</strong> con sugerencia exacta
            </>
          ) : (
            "Cargando…"
          )}
        </p>
        <div className="flex items-center gap-2">
          <BotonExportarConciliacion
            idTarjeta={aplicados.idTarjeta}
            fechaCierreDesde={aplicados.fechaCierreDesde}
            fechaCierreHasta={aplicados.fechaCierreHasta}
          />
          <button
            type="button"
            onClick={() => setVerExactas(true)}
            className="rounded-sm bg-finance px-4 py-2 text-sm text-white hover:opacity-90"
          >
            Aceptar sugerencias exactas…
          </button>
        </div>
      </div>

      <FilterBar
        onSubmit={(e) => {
          e.preventDefault();
          setAplicados(form);
          setPage(1);
        }}
      >
        <FilterField label="Tarjeta">
          <select className={filterInputClass} value={form.idTarjeta} onChange={(e) => setForm({ ...form, idTarjeta: e.target.value })}>
            <option value="">Todas</option>
            {tarjetas?.map((t) => (
              <option key={t.idTarjeta} value={t.idTarjeta}>
                {t.nombre}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Proveedor">
          <input className={filterInputClass} value={form.proveedor} onChange={(e) => setForm({ ...form, proveedor: e.target.value })} placeholder="Razón social…" />
        </FilterField>
        <FilterField label="Cierre desde">
          <input type="date" className={filterInputClass} value={form.fechaCierreDesde} onChange={(e) => setForm({ ...form, fechaCierreDesde: e.target.value })} />
        </FilterField>
        <FilterField label="Cierre hasta">
          <input type="date" className={filterInputClass} value={form.fechaCierreHasta} onChange={(e) => setForm({ ...form, fechaCierreHasta: e.target.value })} />
        </FilterField>
        <label className="flex items-center gap-1.5 self-center text-sm text-ink-secondary">
          <input type="checkbox" checked={form.soloConSugerencia} onChange={(e) => setForm({ ...form, soloConSugerencia: e.target.checked })} />
          Solo con sugerencia
        </label>
        <FilterSubmitButton />
      </FilterBar>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="No se pudieron cargar las líneas pendientes." onRetry={() => refetch()} />}
      {data && (
        <DataTable
          columns={columnas}
          rows={data.items}
          keyField={(r) => r.idLineaConsumo}
          emptyMessage="No hay líneas pendientes con estos filtros."
          page={data.page}
          pageSize={data.pageSize}
          total={data.total}
          onPageChange={setPage}
        />
      )}

      <PanelConciliacion idLineaConsumo={abierta} onClose={() => setAbierta(null)} onChanged={refrescar} />
      {verExactas && (
        <ModalExactas
          onClose={() => setVerExactas(false)}
          onApplied={() => {
            setVerExactas(false);
            refrescar();
          }}
        />
      )}
    </div>
  );
}
