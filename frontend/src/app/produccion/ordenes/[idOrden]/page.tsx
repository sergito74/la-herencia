"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError } from "@/services/apiClient";
import {
  agregarMaquinaria,
  anularOrden,
  corregirFechaEjecucion,
  ejecutarOrden,
  fetchOrden,
} from "@/services/ordenesApi";
import { formatCantidad, formatMoneda, formatFecha } from "@/lib/format";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { NumberInput } from "@/components/ui/NumberInput";
import { useToast } from "@/components/ui/Toast";
import { BadgeEstadoOrden } from "@/components/ordenes/EstadosOrden";
import { DevolucionPanel } from "@/components/ordenes/DevolucionPanel";
import { HectareasAplicadasPanel } from "@/components/ordenes/HectareasAplicadasPanel";
import { FormularioRetiroView } from "@/components/ordenes/FormularioRetiroView";
import { PageHeader } from "@/components/ui/PageHeader";
import { CultivoChip } from "@/components/cultivos/CultivoChip";

export default function DetalleOrdenPage() {
  const { idOrden } = useParams<{ idOrden: string }>();
  const id = Number(idOrden);
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { data: orden, isLoading, isError, refetch } = useQuery({ queryKey: ["orden", id], queryFn: () => fetchOrden(id), staleTime: 0 });
  const [motivo, setMotivo] = useState("");
  const [anulando, setAnulando] = useState(false);
  const [ejecutando, setEjecutando] = useState(false);
  const [fechaEjecucion, setFechaEjecucion] = useState(new Date().toISOString().slice(0, 10));
  const [corrigiendoFecha, setCorrigiendoFecha] = useState(false);
  const [fechaEjecucionCorregida, setFechaEjecucionCorregida] = useState("");
  const [descMaquinaria, setDescMaquinaria] = useState("");
  const [costoMaquinaria, setCostoMaquinaria] = useState<number | null>(null);

  function refrescar() {
    refetch();
    qc.invalidateQueries({ queryKey: ["ordenes"] });
  }

  async function confirmarEjecucion() {
    try {
      await ejecutarOrden(id, fechaEjecucion);
      showToast("Orden marcada como ejecutada.", "success");
      setEjecutando(false);
      refrescar();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo ejecutar la orden.", "danger");
    }
  }

  async function confirmarCorreccionFecha() {
    try {
      await corregirFechaEjecucion(id, fechaEjecucionCorregida);
      showToast("Fecha de ejecución corregida.", "success");
      setCorrigiendoFecha(false);
      refrescar();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo corregir la fecha.", "danger");
    }
  }

  async function confirmarAnulacion() {
    try {
      await anularOrden(id, motivo);
      showToast("Orden anulada. El stock consumido se liberó.", "success");
      setAnulando(false);
      refrescar();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo anular la orden.", "danger");
    }
  }

  async function guardarMaquinaria() {
    if (!costoMaquinaria || !descMaquinaria.trim()) return;
    try {
      await agregarMaquinaria(id, { descripcion: descMaquinaria, costoPorHectarea: costoMaquinaria });
      showToast("Maquinaria agregada y prorrateada entre los lotes de la orden.", "success");
      setDescMaquinaria("");
      setCostoMaquinaria(null);
      refrescar();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo agregar la maquinaria.", "danger");
    }
  }

  if (isLoading) return <LoadingState />;
  if (isError || !orden) return <ErrorState message="No se pudo cargar la orden." onRetry={refetch} />;

  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader
        titulo={<span className="inline-flex items-center gap-2">Orden N° {orden.idOrden} <BadgeEstadoOrden estado={orden.estado} /></span>}
        volver="/produccion/ordenes"
      >
          {orden.editable && (
            <Link href={`/produccion/ordenes/${orden.idOrden}/editar`} className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken">
              Editar
            </Link>
          )}
          {orden.estado === "Planificada" && (
            <button type="button" onClick={() => setEjecutando(true)} className="rounded bg-finance px-3 py-1.5 text-sm text-white">
              Marcar ejecutada
            </button>
          )}
          {orden.estado !== "Anulada" && (
            <button type="button" onClick={() => setAnulando(true)} className="rounded border border-status-danger px-3 py-1.5 text-sm text-status-danger hover:bg-status-danger-bg">
              Anular
            </button>
          )}
      </PageHeader>

      <div className="grid grid-cols-2 gap-x-6 gap-y-1 rounded border border-border bg-surface-sunken/50 px-3 py-2 text-sm sm:grid-cols-5">
        <div>
          <div className="text-xs text-ink-secondary">Fecha pedido</div>
          <div>{formatFecha(orden.fechaPedido)}</div>
        </div>
        <div>
          <div className="text-xs text-ink-secondary">Fecha ejecución</div>
          <div className="flex items-center gap-2">
            {formatFecha(orden.fechaEjecucion)}
            {orden.estado === "Ejecutada" && (
              <button
                type="button"
                onClick={() => {
                  setFechaEjecucionCorregida(orden.fechaEjecucion ?? new Date().toISOString().slice(0, 10));
                  setCorrigiendoFecha(true);
                }}
                className="text-xs text-finance underline"
              >
                Corregir
              </button>
            )}
          </div>
        </div>
        <div>
          <div className="text-xs text-ink-secondary">Labor</div>
          <div>{orden.tipoLabor ?? "—"}</div>
        </div>
        <div>
          <div className="text-xs text-ink-secondary">Contratista</div>
          <div className="truncate" title={orden.contratista ?? undefined}>{orden.contratista ?? "Maquinaria propia"}</div>
        </div>
        <div>
          <div className="text-xs text-ink-secondary">Superficie</div>
          <div className="font-data">{formatCantidad(orden.hectareas)} ha</div>
        </div>
      </div>

      {orden.motivoAnulacion && (
        <p className="mt-2 rounded border border-status-danger bg-status-danger-bg px-3 py-1.5 text-sm text-status-danger">Motivo de anulación: {orden.motivoAnulacion}</p>
      )}

      {corrigiendoFecha && (
        <div className="mt-2 flex flex-wrap items-end gap-2 rounded border border-border p-2">
          <label className="text-sm">
            Fecha de ejecución correcta
            <input type="date" className="mt-1 block w-full rounded border border-border px-2 py-1" value={fechaEjecucionCorregida} onChange={(e) => setFechaEjecucionCorregida(e.target.value)} />
          </label>
          <div className="flex gap-2">
            <button type="button" onClick={confirmarCorreccionFecha} disabled={!fechaEjecucionCorregida} className="rounded bg-finance px-3 py-1.5 text-sm text-white disabled:opacity-50">
              Guardar corrección
            </button>
            <button type="button" onClick={() => setCorrigiendoFecha(false)} className="rounded border border-border px-3 py-1.5 text-sm">
              Cancelar
            </button>
          </div>
        </div>
      )}

      {ejecutando && (
        <div className="mt-2 flex flex-wrap items-end gap-2 rounded border border-border p-2">
          <label className="text-sm">
            Fecha de ejecución
            <input type="date" className="mt-1 block w-full rounded border border-border px-2 py-1" value={fechaEjecucion} onChange={(e) => setFechaEjecucion(e.target.value)} />
          </label>
          <div className="flex gap-2">
            <button type="button" onClick={confirmarEjecucion} disabled={!fechaEjecucion} className="rounded bg-finance px-3 py-1.5 text-sm text-white disabled:opacity-50">
              Confirmar ejecución
            </button>
            <button type="button" onClick={() => setEjecutando(false)} className="rounded border border-border px-3 py-1.5 text-sm">
              Cancelar
            </button>
          </div>
        </div>
      )}

      {anulando && (
        <div className="mt-2 flex flex-wrap items-end gap-2 rounded border border-status-danger p-2">
          <label className="min-w-[20rem] flex-1 text-sm">
            Motivo de la anulación
            <input className="mt-1 block w-full rounded border border-border px-2 py-1" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          </label>
          <div className="flex gap-2">
            <button type="button" onClick={confirmarAnulacion} disabled={!motivo.trim()} className="rounded bg-status-danger px-3 py-1.5 text-sm text-white disabled:opacity-50">
              Confirmar anulación
            </button>
            <button type="button" onClick={() => setAnulando(false)} className="rounded border border-border px-3 py-1.5 text-sm">
              Cancelar
            </button>
          </div>
        </div>
      )}

      <div className="mt-3 space-y-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-secondary">Insumos y distribución</h2>
        {orden.insumos.map((r) => (
          <div key={r.idOrdenInsumo} className="rounded border border-border">
            <div className="border-b border-border bg-surface-sunken/60 px-3 py-1.5 text-sm font-medium">
              {r.producto ?? r.idProducto} — {formatCantidad(r.cantidadTotal)} {r.unidad}
              {Math.abs(r.ajusteRecuento) > 0.00005 && (
                <span className="ml-2 text-xs font-normal text-ink-secondary" title="Se reparte entre los lotes en la misma proporción">
                  Ajuste por recuento físico: {r.ajusteRecuento > 0 ? "+" : ""}
                  {formatCantidad(r.ajusteRecuento)} → consumo efectivo {formatCantidad(r.cantidadTotal + r.ajusteRecuento)} {r.unidad}
                </span>
              )}
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-ink-secondary">
                  <th className="px-3 py-1">Lote</th>
                  <th className="py-1 pr-3">Cultivo</th>
                  <th className="py-1 pr-3">Campaña</th>
                  <th className="py-1 pr-3 text-right">Dosis/ha</th>
                  <th className="py-1 pr-3 text-right">Superficie</th>
                  <th className="py-1 pr-3 text-right">Cantidad</th>
                  <th className="py-1 pr-3">Aplicado</th>
                </tr>
              </thead>
              <tbody>
                {r.distribuciones.map((d) => (
                  <tr key={d.idDistrib} className="border-t border-border">
                    <td className="px-3 py-0.5">{d.lote}</td>
                    <td className="py-0.5 pr-3"><CultivoChip cultivo={d.cultivo} /></td>
                    <td className="py-0.5 pr-3">{d.campania}</td>
                    <td className="py-0.5 pr-3 text-right font-data">{formatCantidad(d.dosisHa)}</td>
                    <td className="py-0.5 pr-3 text-right font-data">{formatCantidad(d.superficie)}</td>
                    <td className="py-0.5 pr-3 text-right font-data">{formatCantidad(d.cantidadAsignada)} {r.unidad}</td>
                    <td className="py-0.5 pr-3">{d.aplicar ? "Sí" : <span className="text-ink-muted">No</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {r.devoluciones.length > 0 && (
              <div className="px-3 pb-1 text-xs text-ink-secondary">
                Devoluciones: {r.devoluciones.map((dv) => `${formatCantidad(dv.cantidad)} (${formatFecha(dv.fecha)})`).join(", ")}
              </div>
            )}
            {orden.estado !== "Anulada" && <div className="px-3 pb-1.5"><DevolucionPanel idOrden={id} renglon={r} onGuardada={refrescar} /></div>}
          </div>
        ))}
      </div>

      {orden.estado === "Ejecutada" && <HectareasAplicadasPanel orden={orden} onGuardada={refrescar} />}

      <div className="mt-3 grid items-start gap-x-4 gap-y-2 lg:grid-cols-2">
      <details open={orden.maquinaria.length > 0} className="rounded border border-border px-3 py-1">
        <summary className="cursor-pointer select-none py-1 text-sm font-semibold uppercase tracking-wide text-ink-secondary">Maquinaria propia{orden.maquinaria.length > 0 && ` (${orden.maquinaria.length})`}</summary>
        {orden.maquinaria.map((m) => (
          <div key={m.idOrdenMaquinaria} className="flex justify-between border-t border-border py-1 text-sm">
            <span>{m.descripcion}</span><span className="font-data">{formatMoneda(m.costoPorHectarea)}/ha</span>
          </div>
        ))}
        {orden.estado !== "Anulada" && (
          <div className="flex flex-wrap items-end gap-2 py-1.5">
            <label className="text-sm">
              Descripción
              <input className="mt-1 block rounded border border-border px-2 py-1" value={descMaquinaria} onChange={(e) => setDescMaquinaria(e.target.value)} />
            </label>
            <label className="text-sm">
              Costo por hectárea
              <NumberInput className="mt-1 block w-28 rounded border border-border px-2 py-1 text-right" value={costoMaquinaria} onChange={setCostoMaquinaria} />
            </label>
            <button type="button" onClick={guardarMaquinaria} disabled={!costoMaquinaria || !descMaquinaria.trim()} className="rounded bg-finance px-3 py-1.5 text-sm text-white disabled:opacity-50">
              Agregar
            </button>
          </div>
        )}
      </details>

      <details open={orden.facturasContratista.length > 0} className="rounded border border-border px-3 py-1">
        <summary className="cursor-pointer select-none py-1 text-sm font-semibold uppercase tracking-wide text-ink-secondary">Facturas del contratista{orden.facturasContratista.length > 0 && ` (${orden.facturasContratista.length})`}</summary>
        {/* 048: solo lectura. Se vinculan desde la factura, en Compras (panel "Órdenes de trabajo"). */}
        {orden.facturasContratista.length === 0 ? (
          <p className="py-1 text-sm text-ink-secondary" title="Se vinculan desde la factura, en Compras">Sin facturas vinculadas (se vinculan desde Compras).</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-ink-secondary">
                <th className="py-1">Documento</th>
                <th className="py-1">Fecha</th>
                <th className="py-1 text-right">Neto</th>
                <th className="py-1">Imputado a esta orden</th>
              </tr>
            </thead>
            <tbody>
              {orden.facturasContratista.flatMap((f) => [f, ...f.notasRelacionadas]).map((d) => (
                <tr key={d.idCompra} className="border-t border-border align-top">
                  <td className="py-1">
                    <Link href={`/compras/${d.idCompra}/editar`} className="text-finance hover:underline">
                      {d.tipoDocumento} {d.numeroDocumento}
                    </Link>
                  </td>
                  <td className="py-1">{formatFecha(d.fecha)}</td>
                  <td className="py-1 text-right">{formatMoneda(d.neto, d.moneda === "Dolares" ? "Dolares" : "Pesos")}</td>
                  <td className="py-1">
                    {d.reparto.length === 0
                      ? "—"
                      : d.reparto.map((r, k) => (
                          <div key={k} className="flex flex-wrap items-center gap-1">
                            {r.cultivo ? <CultivoChip cultivo={r.cultivo} /> : "Sin cultivo"} {r.campania ?? ""} {r.lote ? `· Lote ${r.lote}` : ""} · <span className="font-data">{formatMoneda(r.importe)}</span>
                          </div>
                        ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </details>
      </div>

      <FormularioRetiroView orden={orden} />
    </main>
  );
}
