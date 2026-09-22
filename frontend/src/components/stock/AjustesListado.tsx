"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { anularAjuste, crearAjuste, fetchAjustes, fetchUnidades, type Ajuste } from "@/services/remitosApi";
import { ApiError } from "@/services/apiClient";
import { formatCantidad, formatMoneda } from "@/lib/format";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { NumberInput } from "@/components/ui/NumberInput";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";
import { ProductoSelect } from "@/components/remitos/ProductoSelect";

const campo = `${filterInputClass} w-full px-1.5 py-1 text-xs`;

function AjusteForm({ abierto, onClose, onCreado }: { abierto: boolean; onClose: () => void; onCreado: () => void }) {
  const { showToast } = useToast();
  const { data: unidades } = useQuery({ queryKey: ["unidades"], queryFn: fetchUnidades, staleTime: Infinity });
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10));
  const [producto, setProducto] = useState<{ idProducto: number; producto: string } | null>(null);
  const [tipo, setTipo] = useState<"faltante" | "sobrante">("faltante");
  const [cantidad, setCantidad] = useState<number | null>(null);
  const [unidad, setUnidad] = useState("LTS");
  const [costo, setCosto] = useState(0);
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [confirmacion, setConfirmacion] = useState<string[] | null>(null);
  const [guardando, setGuardando] = useState(false);

  async function guardar(confirmar: boolean) {
    setError(null);
    if (!producto) return setError("Elegí el producto.");
    if (!cantidad || cantidad <= 0) return setError("La cantidad debe ser mayor a cero.");
    if (!motivo.trim()) return setError("Indicá el motivo del ajuste (por ejemplo «conteo físico»).");
    setGuardando(true);
    try {
      await crearAjuste({
        fecha, idProducto: producto.idProducto, unidad, motivo: motivo.trim(), confirmar,
        cantidad: tipo === "faltante" ? -cantidad : cantidad,
        costoUnitario: tipo === "sobrante" && costo > 0 ? costo : null,
      });
      showToast(tipo === "faltante" ? "Faltante registrado: salió del stock." : "Sobrante registrado: entró como una nueva capa.", "success");
      setProducto(null);
      setCantidad(null);
      setMotivo("");
      setConfirmacion(null);
      onCreado();
      onClose();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setConfirmacion(e.message.split(/(?<=\.)\s+/));
      else setError(e instanceof ApiError ? e.message : "No se pudo registrar el ajuste.");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <SideDrawer open={abierto} onClose={onClose} title="Nuevo ajuste de inventario" maxWidthClass="max-w-2xl">
      <p className="text-xs text-ink-secondary">Corrige diferencias entre el stock físico y el del sistema. Un faltante sale por FIFO; un sobrante entra como una capa nueva.</p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="text-xs text-ink-secondary">
          Fecha
          <input type="date" className={campo} value={fecha} onChange={(e) => setFecha(e.target.value)} />
        </label>
        <div className="text-xs text-ink-secondary">
          Tipo
          <div className="mt-1 flex gap-4">
            {(["faltante", "sobrante"] as const).map((t) => (
              <label key={t} className="flex items-center gap-1 text-ink-primary">
                <input type="radio" checked={tipo === t} onChange={() => setTipo(t)} />
                {t === "faltante" ? "Faltante (hay menos)" : "Sobrante (hay más)"}
              </label>
            ))}
          </div>
        </div>
        <div className="text-xs text-ink-secondary sm:col-span-2">
          Producto
          <ProductoSelect
            value={producto}
            onChange={(p) => {
              setProducto({ idProducto: p.idProducto, producto: p.producto });
              if (p.unidadBase) setUnidad(p.unidadBase);
            }}
          />
        </div>
        <label className="text-xs text-ink-secondary">
          Cantidad
          <NumberInput className={`${campo} text-right font-data`} value={cantidad} onChange={setCantidad} />
        </label>
        <label className="text-xs text-ink-secondary">
          Unidad
          <select className={campo} value={unidad} onChange={(e) => setUnidad(e.target.value)}>
            {unidades?.map((u) => (
              <option key={u.codigo} value={u.codigo}>
                {u.codigo}
              </option>
            ))}
          </select>
        </label>
        {tipo === "sobrante" && (
          <label className="text-xs text-ink-secondary sm:col-span-2">
            Costo unitario (opcional; si no lo indicás toma el de la capa anterior)
            <MoneyInput className={`${campo} text-right font-data`} value={costo} moneda="Pesos" onChange={setCosto} />
          </label>
        )}
        <label className="text-xs text-ink-secondary sm:col-span-2">
          Motivo
          <input className={campo} value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={255} placeholder="Conteo físico, derrame, error de carga…" />
        </label>
      </div>
      {confirmacion && (
        <div className="mt-3 rounded-md border border-status-warning bg-status-warning-bg p-3 text-xs">
          <ul className="list-disc pl-4">
            {confirmacion.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
          <div className="mt-2 flex gap-2">
            <button type="button" className="rounded-sm bg-finance px-3 py-1 text-white" onClick={() => guardar(true)} disabled={guardando}>
              Registrar igual
            </button>
            <button type="button" className="rounded-sm border border-border px-3 py-1" onClick={() => setConfirmacion(null)}>
              Volver
            </button>
          </div>
        </div>
      )}
      {error && <p className="mt-3 text-sm text-status-danger">{error}</p>}
      <div className="mt-4 flex gap-2">
        <button type="button" disabled={guardando} onClick={() => guardar(false)} className="rounded-sm bg-finance px-5 py-2 text-sm text-white hover:opacity-90 disabled:opacity-40">
          {guardando ? "Guardando…" : "Registrar ajuste"}
        </button>
        <button type="button" onClick={onClose} className="rounded-sm border border-border px-5 py-2 text-sm text-ink-secondary">
          Cancelar
        </button>
      </div>
    </SideDrawer>
  );
}

/** Ajustes de inventario (010): faltantes y sobrantes. */
export function AjustesListado() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [form, setForm] = useState({ fechaDesde: "", fechaHasta: "", producto: "" });
  const [aplicados, setAplicados] = useState(form);
  const [page, setPage] = useState(1);
  const [nuevo, setNuevo] = useState(false);
  const [anulando, setAnulando] = useState<number | null>(null);
  const [motivoAnul, setMotivoAnul] = useState("");
  const filtros = { fechaDesde: aplicados.fechaDesde || undefined, fechaHasta: aplicados.fechaHasta || undefined, producto: aplicados.producto || undefined };
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["ajustes", filtros, page], queryFn: () => fetchAjustes(filtros, page), staleTime: 0 });

  function refrescar() {
    qc.invalidateQueries({ queryKey: ["ajustes"] });
    qc.invalidateQueries({ queryKey: ["existencias"] });
  }

  async function anular(id: number) {
    try {
      await anularAjuste(id, motivoAnul);
      showToast("Ajuste anulado.", "success");
      setAnulando(null);
      setMotivoAnul("");
      refrescar();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo anular el ajuste.", "danger");
    }
  }

  const columnas: DataTableColumn<Ajuste>[] = [
    { key: "fecha", header: "Fecha", numeric: true, render: (a) => a.fecha ?? "—" },
    { key: "producto", header: "Producto", render: (a) => a.producto ?? `Producto ${a.idProducto}` },
    {
      key: "tipo",
      header: "Ajuste",
      numeric: true,
      align: "right",
      render: (a) => (
        <span className={a.cantidad < 0 ? "text-status-danger" : "text-status-success"}>
          {a.cantidad > 0 ? "+" : ""}
          {formatCantidad(a.cantidad)} {a.unidadBase}
        </span>
      ),
    },
    { key: "costo", header: "Costo unit.", numeric: true, align: "right", render: (a) => (a.costoUnitario != null ? formatMoneda(a.costoUnitario) : "—") },
    {
      key: "motivo",
      header: "Motivo",
      render: (a) => (
        <span>
          {a.motivo}
          {a.anulado && (
            <span className="ml-1">
              <StatusBadge label="Anulado" tone="danger" />
            </span>
          )}
        </span>
      ),
    },
    {
      key: "acc",
      header: "",
      render: (a) =>
        a.anulado ? null : anulando === a.idAjuste ? (
          <span className="flex items-center gap-1">
            <input className={`${filterInputClass} w-36 px-1 py-0.5 text-xs`} placeholder="Motivo" value={motivoAnul} onChange={(e) => setMotivoAnul(e.target.value)} />
            <button type="button" disabled={!motivoAnul.trim()} className="text-xs text-status-danger underline disabled:opacity-40" onClick={() => anular(a.idAjuste)}>
              OK
            </button>
            <button type="button" className="text-xs text-ink-secondary" onClick={() => setAnulando(null)}>
              ✕
            </button>
          </span>
        ) : (
          <button type="button" className="text-xs text-ink-secondary underline hover:text-status-danger" onClick={() => setAnulando(a.idAjuste)}>
            Anular
          </button>
        ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button type="button" onClick={() => setNuevo(true)} className="rounded-sm bg-finance px-4 py-2 text-sm text-white hover:opacity-90">
          + Nuevo ajuste
        </button>
      </div>
      <FilterBar
        onSubmit={(e) => {
          e.preventDefault();
          setAplicados(form);
          setPage(1);
        }}
      >
        <FilterField label="Desde">
          <input type="date" className={filterInputClass} value={form.fechaDesde} onChange={(e) => setForm({ ...form, fechaDesde: e.target.value })} />
        </FilterField>
        <FilterField label="Hasta">
          <input type="date" className={filterInputClass} value={form.fechaHasta} onChange={(e) => setForm({ ...form, fechaHasta: e.target.value })} />
        </FilterField>
        <FilterField label="Producto">
          <input className={filterInputClass} value={form.producto} onChange={(e) => setForm({ ...form, producto: e.target.value })} />
        </FilterField>
        <FilterSubmitButton />
      </FilterBar>
      {isLoading && <LoadingState />}
      {isError && <ErrorState message="No se pudieron cargar los ajustes." onRetry={() => refetch()} />}
      {data && <DataTable columns={columnas} rows={data.items} keyField={(a) => a.idAjuste} emptyMessage="No hay ajustes de inventario." page={data.page} pageSize={data.pageSize} total={data.total} onPageChange={setPage} />}
      <AjusteForm abierto={nuevo} onClose={() => setNuevo(false)} onCreado={refrescar} />
    </div>
  );
}
