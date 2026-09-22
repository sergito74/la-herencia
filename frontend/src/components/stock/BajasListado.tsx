"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import {
  anularBaja,
  crearBaja,
  fetchBajas,
  fetchOpcionesBajas,
  fetchUnidades,
  urlExportarBajas,
  type Baja,
} from "@/services/remitosApi";
import { ApiError } from "@/services/apiClient";
import { formatCantidad, formatMoneda } from "@/lib/format";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { KpiCard } from "@/components/ui/KpiCard";
import { NumberInput } from "@/components/ui/NumberInput";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";
import { BotonExcel } from "@/components/remitos/EstadosRemito";
import { ProductoSelect } from "@/components/remitos/ProductoSelect";

const campo = `${filterInputClass} w-full px-1.5 py-1 text-xs`;
let n = 0;

interface Renglon {
  clave: number;
  producto: { idProducto: number; producto: string } | null;
  unidadBase: string | null;
  cantidad: number | null;
  unidad: string;
}
const nuevoRenglon = (): Renglon => ({ clave: ++n, producto: null, unidadBase: null, cantidad: null, unidad: "LTS" });

function BajaForm({ abierto, onClose, onCreada }: { abierto: boolean; onClose: () => void; onCreada: () => void }) {
  const { showToast } = useToast();
  const { data: opciones } = useQuery({ queryKey: ["opciones-bajas"], queryFn: fetchOpcionesBajas, staleTime: Infinity });
  const { data: unidades } = useQuery({ queryKey: ["unidades"], queryFn: fetchUnidades, staleTime: Infinity });
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10));
  const [motivo, setMotivo] = useState("Deterioro");
  const [detalle, setDetalle] = useState("");
  const [idRubro, setIdRubro] = useState<number | "">("");
  const [idCentro, setIdCentro] = useState<number | "">("");
  const [renglones, setRenglones] = useState<Renglon[]>([nuevoRenglon()]);
  const [error, setError] = useState<string | null>(null);
  const [confirmacion, setConfirmacion] = useState<string[] | null>(null);
  const [guardando, setGuardando] = useState(false);

  // Rubro por defecto según el motivo: uso interno → Mantenimiento; el resto → Pérdidas y bajas de insumos
  useEffect(() => {
    if (!opciones) return;
    if (motivo === "UsoInterno") {
      const mant = opciones.rubros.find((r) => r.rubro.startsWith("Mantenimiento"));
      setIdRubro(mant?.idRubro ?? "");
    } else {
      setIdRubro(opciones.rubroPerdidas ?? "");
    }
  }, [motivo, opciones]);

  async function guardar(confirmar: boolean) {
    setError(null);
    if (!idRubro || !idCentro) return setError("Elegí el rubro y el centro de costos donde se imputa el gasto.");
    if (motivo === "Otro" && !detalle.trim()) return setError("Indicá el detalle cuando el motivo es «Otro».");
    const validos = renglones.filter((r) => r.producto || r.cantidad);
    if (validos.length === 0) return setError("Elegí al menos un producto.");
    for (const [i, r] of validos.entries()) {
      if (!r.producto) return setError(`Renglón ${i + 1}: elegí el producto.`);
      if (!r.cantidad || r.cantidad <= 0) return setError(`Renglón ${i + 1}: la cantidad debe ser mayor a cero.`);
    }
    setGuardando(true);
    try {
      await crearBaja({
        fecha, motivo, detalle: detalle.trim() || null, idRubro, idCentro, confirmar,
        renglones: validos.map((r) => ({ idProducto: r.producto!.idProducto, cantidad: r.cantidad!, unidad: r.unidad })),
      });
      showToast("Baja registrada: salió del stock y queda como gasto de la empresa.", "success");
      setRenglones([nuevoRenglon()]);
      setDetalle("");
      setConfirmacion(null);
      onCreada();
      onClose();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setConfirmacion(e.message.split(/(?<=\.)\s+/));
      else setError(e instanceof ApiError ? e.message : "No se pudo registrar la baja.");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <SideDrawer open={abierto} onClose={onClose} title="Nueva baja de stock" maxWidthClass="max-w-3xl">
      <p className="text-xs text-ink-secondary">
        Para insumos que salen del stock sin usarse en una orden de trabajo. No se vinculan a ningún cultivo ni campaña: se valorizan por FIFO y quedan como gasto de la empresa.
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="text-xs text-ink-secondary">
          Fecha
          <input type="date" className={campo} value={fecha} onChange={(e) => setFecha(e.target.value)} />
        </label>
        <label className="text-xs text-ink-secondary">
          Motivo
          <select className={campo} value={motivo} onChange={(e) => setMotivo(e.target.value)}>
            {opciones?.motivos.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-ink-secondary sm:col-span-2">
          Detalle {motivo === "Otro" ? "(obligatorio)" : "(opcional)"}
          <input className={campo} value={detalle} onChange={(e) => setDetalle(e.target.value)} maxLength={255} />
        </label>
        <label className="text-xs text-ink-secondary">
          Rubro del gasto
          <select className={campo} value={idRubro} onChange={(e) => setIdRubro(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Elegir…</option>
            {opciones?.rubros.map((r) => (
              <option key={r.idRubro} value={r.idRubro}>
                {r.rubro}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-ink-secondary">
          Centro de costos
          <select className={campo} value={idCentro} onChange={(e) => setIdCentro(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Elegir…</option>
            {opciones?.centros.map((c) => (
              <option key={c.idCentro} value={c.idCentro}>
                {c.centro}
              </option>
            ))}
          </select>
        </label>
      </div>

      <table className="mt-4 w-full text-xs">
        <thead className="text-left text-ink-secondary">
          <tr>
            <th className="py-1 pr-2">Producto</th>
            <th className="w-24 pr-2">Cantidad</th>
            <th className="w-24 pr-2">Unidad</th>
            <th className="w-6" />
          </tr>
        </thead>
        <tbody>
          {renglones.map((r) => (
            <tr key={r.clave} className="border-t border-border align-top">
              <td className="py-1 pr-2">
                <ProductoSelect
                  value={r.producto}
                  onChange={(p) => setRenglones((prev) => prev.map((x) => (x.clave === r.clave ? { ...x, producto: { idProducto: p.idProducto, producto: p.producto }, unidadBase: p.unidadBase, unidad: p.unidadBase ?? x.unidad } : x)))}
                />
                {r.producto && !r.unidadBase && <span className="text-[11px] text-status-warning">Este producto todavía no tiene unidad base (se define al cargar su primer remito).</span>}
              </td>
              <td className="py-1 pr-2">
                <NumberInput className={`${campo} text-right font-data`} value={r.cantidad} onChange={(v) => setRenglones((prev) => prev.map((x) => (x.clave === r.clave ? { ...x, cantidad: v } : x)))} />
              </td>
              <td className="py-1 pr-2">
                <select className={campo} value={r.unidad} onChange={(e) => setRenglones((prev) => prev.map((x) => (x.clave === r.clave ? { ...x, unidad: e.target.value } : x)))}>
                  {unidades?.map((u) => (
                    <option key={u.codigo} value={u.codigo}>
                      {u.codigo}
                    </option>
                  ))}
                </select>
              </td>
              <td className="py-1">
                {renglones.length > 1 && (
                  <button type="button" className="text-ink-secondary hover:text-status-danger" onClick={() => setRenglones((p) => p.filter((x) => x.clave !== r.clave))}>
                    ✕
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button type="button" className="mt-2 text-xs text-finance underline" onClick={() => setRenglones((p) => [...p, nuevoRenglon()])}>
        + Agregar producto
      </button>

      {confirmacion && (
        <div className="mt-3 rounded-md border border-status-warning bg-status-warning-bg p-3 text-xs">
          <ul className="list-disc pl-4">
            {confirmacion.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
          <div className="mt-2 flex gap-2">
            <button type="button" className="rounded-sm bg-finance px-3 py-1 text-white" disabled={guardando} onClick={() => guardar(true)}>
              Dar de baja igual
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
          {guardando ? "Guardando…" : "Registrar baja"}
        </button>
        <button type="button" onClick={onClose} className="rounded-sm border border-border px-5 py-2 text-sm text-ink-secondary">
          Cancelar
        </button>
      </div>
    </SideDrawer>
  );
}

/** Bajas de stock (010): salidas sin orden de trabajo, imputadas como gasto de la empresa. */
export function BajasListado() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [form, setForm] = useState({ fechaDesde: "", fechaHasta: "", motivo: "", producto: "" });
  const [aplicados, setAplicados] = useState(form);
  const [page, setPage] = useState(1);
  const [nueva, setNueva] = useState(false);
  const [anulando, setAnulando] = useState<number | null>(null);
  const [motivoAnul, setMotivoAnul] = useState("");
  const { data: opciones } = useQuery({ queryKey: ["opciones-bajas"], queryFn: fetchOpcionesBajas, staleTime: Infinity });
  const filtros = { fechaDesde: aplicados.fechaDesde || undefined, fechaHasta: aplicados.fechaHasta || undefined, motivo: aplicados.motivo || undefined, producto: aplicados.producto || undefined };
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["bajas", filtros, page], queryFn: () => fetchBajas({ ...filtros, incluirAnuladas: true }, page), staleTime: 0 });

  function refrescar() {
    qc.invalidateQueries({ queryKey: ["bajas"] });
    qc.invalidateQueries({ queryKey: ["existencias"] });
  }

  async function anular(id: number) {
    try {
      await anularBaja(id, motivoAnul);
      showToast("Baja anulada: el stock se restituyó.", "success");
      setAnulando(null);
      setMotivoAnul("");
      refrescar();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo anular la baja.", "danger");
    }
  }

  const columnas: DataTableColumn<Baja>[] = [
    { key: "fecha", header: "Fecha", numeric: true, render: (b) => b.fecha ?? "—" },
    {
      key: "motivo",
      header: "Motivo",
      render: (b) => (
        <span>
          {b.motivoLabel}
          {b.detalle && <span className="block text-xs text-ink-secondary">{b.detalle}</span>}
          {b.anulada && <StatusBadge label="Anulada" tone="danger" />}
        </span>
      ),
    },
    { key: "imputacion", header: "Rubro / centro", render: (b) => <span className="text-xs">{b.rubro}<span className="block text-ink-secondary">{b.centro}</span></span> },
    {
      key: "productos",
      header: "Productos",
      render: (b) => (
        <span className="text-xs">
          {b.renglones.map((r) => `${r.producto} (${formatCantidad(r.cantidad)} ${r.unidadBase ?? ""})`).join(", ")}
        </span>
      ),
    },
    {
      key: "gasto",
      header: "Gasto (FIFO)",
      numeric: true,
      align: "right",
      render: (b) => (
        <span>
          {formatMoneda(b.gasto)}
          {b.costoPendiente && <span className="block"><StatusBadge label="Costo pendiente" tone="warning" /></span>}
        </span>
      ),
    },
    {
      key: "acc",
      header: "",
      render: (b) =>
        b.anulada ? null : anulando === b.idBaja ? (
          <span className="flex items-center gap-1">
            <input className={`${filterInputClass} w-36 px-1 py-0.5 text-xs`} placeholder="Motivo" value={motivoAnul} onChange={(e) => setMotivoAnul(e.target.value)} />
            <button type="button" disabled={!motivoAnul.trim()} className="text-xs text-status-danger underline disabled:opacity-40" onClick={() => anular(b.idBaja)}>
              OK
            </button>
            <button type="button" className="text-xs text-ink-secondary" onClick={() => setAnulando(null)}>
              ✕
            </button>
          </span>
        ) : (
          <button type="button" className="text-xs text-ink-secondary underline hover:text-status-danger" onClick={() => setAnulando(b.idBaja)}>
            Anular
          </button>
        ),
    },
  ];

  return (
    <div className="space-y-4">
      {data && (
        <div className="grid gap-3 sm:grid-cols-3">
          <KpiCard label="Bajas (con estos filtros)" value={formatCantidad(data.total)} />
          <KpiCard label="Gasto de la página (FIFO)" value={formatMoneda(data.gastoTotal)} tone="danger" />
        </div>
      )}
      <div className="flex justify-end gap-2">
        <BotonExcel href={urlExportarBajas(filtros)} />
        <button type="button" onClick={() => setNueva(true)} className="rounded-sm bg-finance px-4 py-2 text-sm text-white hover:opacity-90">
          + Nueva baja
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
        <FilterField label="Motivo">
          <select className={filterInputClass} value={form.motivo} onChange={(e) => setForm({ ...form, motivo: e.target.value })}>
            <option value="">Todos</option>
            {opciones?.motivos.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Producto">
          <input className={filterInputClass} value={form.producto} onChange={(e) => setForm({ ...form, producto: e.target.value })} />
        </FilterField>
        <FilterSubmitButton />
      </FilterBar>
      {isLoading && <LoadingState />}
      {isError && <ErrorState message="No se pudieron cargar las bajas." onRetry={() => refetch()} />}
      {data && <DataTable columns={columnas} rows={data.items} keyField={(b) => b.idBaja} emptyMessage="No hay bajas registradas." page={data.page} pageSize={data.pageSize} total={data.total} onPageChange={setPage} />}
      <BajaForm abierto={nueva} onClose={() => setNueva(false)} onCreada={refrescar} />
    </div>
  );
}
