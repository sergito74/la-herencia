"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError } from "@/services/apiClient";
import { agregarMaquinaria, anularOrden, ejecutarOrden, fetchOrden, vincularFacturaContratista } from "@/services/ordenesApi";
import { formatCantidad, formatMoneda } from "@/lib/format";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { NumberInput } from "@/components/ui/NumberInput";
import { useToast } from "@/components/ui/Toast";
import { BadgeEstadoOrden } from "@/components/ordenes/EstadosOrden";
import { DevolucionPanel } from "@/components/ordenes/DevolucionPanel";
import { FormularioRetiroView } from "@/components/ordenes/FormularioRetiroView";

export default function DetalleOrdenPage() {
  const { idOrden } = useParams<{ idOrden: string }>();
  const id = Number(idOrden);
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { data: orden, isLoading, isError, refetch } = useQuery({ queryKey: ["orden", id], queryFn: () => fetchOrden(id), staleTime: 0 });
  const [motivo, setMotivo] = useState("");
  const [anulando, setAnulando] = useState(false);
  const [descMaquinaria, setDescMaquinaria] = useState("");
  const [costoMaquinaria, setCostoMaquinaria] = useState<number | null>(null);
  const [idCompraFactura, setIdCompraFactura] = useState<number | null>(null);

  function refrescar() {
    refetch();
    qc.invalidateQueries({ queryKey: ["ordenes"] });
  }

  async function marcarEjecutada() {
    try {
      await ejecutarOrden(id, new Date().toISOString().slice(0, 10));
      showToast("Orden marcada como ejecutada.", "success");
      refrescar();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo ejecutar la orden.", "danger");
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

  async function guardarFactura() {
    if (!idCompraFactura) return;
    try {
      await vincularFacturaContratista(id, idCompraFactura);
      showToast("Factura del contratista vinculada.", "success");
      setIdCompraFactura(null);
      refrescar();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo vincular la factura.", "danger");
    }
  }

  if (isLoading) return <LoadingState />;
  if (isError || !orden) return <ErrorState message="No se pudo cargar la orden." onRetry={refetch} />;

  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">
          Orden N° {orden.idOrden} <BadgeEstadoOrden estado={orden.estado} />
        </h1>
        <div className="flex gap-2">
          {orden.editable && (
            <Link href={`/produccion/ordenes/${orden.idOrden}/editar`} className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken">
              Editar
            </Link>
          )}
          {orden.estado === "Planificada" && (
            <button type="button" onClick={marcarEjecutada} className="rounded bg-finance px-3 py-1.5 text-sm text-white">
              Marcar ejecutada
            </button>
          )}
          {orden.estado !== "Anulada" && (
            <button type="button" onClick={() => setAnulando(true)} className="rounded border border-status-danger px-3 py-1.5 text-sm text-status-danger hover:bg-status-danger-bg">
              Anular
            </button>
          )}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
        <div>
          <div className="text-ink-secondary">Fecha pedido</div>
          <div>{orden.fechaPedido ?? "—"}</div>
        </div>
        <div>
          <div className="text-ink-secondary">Fecha ejecución</div>
          <div>{orden.fechaEjecucion ?? "—"}</div>
        </div>
        <div>
          <div className="text-ink-secondary">Labor</div>
          <div>{orden.tipoLabor ?? "—"}</div>
        </div>
        <div>
          <div className="text-ink-secondary">Contratista</div>
          <div>{orden.contratista ?? "Maquinaria propia"}</div>
        </div>
      </div>

      {orden.motivoAnulacion && (
        <p className="mt-3 rounded border border-status-danger bg-status-danger-bg p-3 text-sm text-status-danger">Motivo de anulación: {orden.motivoAnulacion}</p>
      )}

      {anulando && (
        <div className="mt-4 rounded border border-status-danger p-3">
          <label className="block text-sm">
            Motivo de la anulación
            <input className="mt-1 w-full rounded border border-border px-2 py-1.5" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          </label>
          <div className="mt-2 flex gap-2">
            <button type="button" onClick={confirmarAnulacion} disabled={!motivo.trim()} className="rounded bg-status-danger px-3 py-1.5 text-sm text-white disabled:opacity-50">
              Confirmar anulación
            </button>
            <button type="button" onClick={() => setAnulando(false)} className="rounded border border-border px-3 py-1.5 text-sm">
              Cancelar
            </button>
          </div>
        </div>
      )}

      <div className="mt-6 space-y-4">
        <h2 className="text-lg font-medium">Insumos y distribución</h2>
        {orden.insumos.map((r) => (
          <div key={r.idOrdenInsumo} className="rounded border border-border p-3">
            <div className="mb-2 font-medium">
              {r.producto ?? r.idProducto} — {formatCantidad(r.cantidadTotal)} {r.unidad}
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-ink-secondary">
                  <th>Lote</th>
                  <th>Cultivo</th>
                  <th>Campaña</th>
                  <th className="text-right">Dosis/ha</th>
                  <th className="text-right">Superficie</th>
                  <th className="text-right">Cantidad</th>
                  <th>Aplicado</th>
                </tr>
              </thead>
              <tbody>
                {r.distribuciones.map((d) => (
                  <tr key={d.idDistrib} className="border-t border-border">
                    <td>{d.lote}</td>
                    <td>{d.cultivo}</td>
                    <td>{d.campania}</td>
                    <td className="text-right">{formatCantidad(d.dosisHa)}</td>
                    <td className="text-right">{formatCantidad(d.superficie)}</td>
                    <td className="text-right">{formatCantidad(d.cantidadAsignada)}</td>
                    <td>{d.aplicar ? "Sí" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {r.devoluciones.length > 0 && (
              <div className="mt-2 text-sm text-ink-secondary">
                Devoluciones: {r.devoluciones.map((dv) => `${formatCantidad(dv.cantidad)} (${dv.fecha})`).join(", ")}
              </div>
            )}
            {orden.estado !== "Anulada" && <DevolucionPanel idOrden={id} renglon={r} onGuardada={refrescar} />}
          </div>
        ))}
      </div>

      <div className="mt-6">
        <h2 className="text-lg font-medium">Maquinaria propia</h2>
        {orden.maquinaria.map((m) => (
          <div key={m.idOrdenMaquinaria} className="mt-2 rounded border border-border p-3 text-sm">
            {m.descripcion} — {formatMoneda(m.costoPorHectarea)}/ha
          </div>
        ))}
        {orden.estado !== "Anulada" && (
          <div className="mt-2 flex flex-wrap items-end gap-2">
            <label className="text-sm">
              Descripción
              <input className="mt-1 block rounded border border-border px-2 py-1.5" value={descMaquinaria} onChange={(e) => setDescMaquinaria(e.target.value)} />
            </label>
            <label className="text-sm">
              Costo por hectárea
              <NumberInput className="mt-1 block w-32 rounded border border-border px-2 py-1.5 text-right" value={costoMaquinaria} onChange={setCostoMaquinaria} />
            </label>
            <button type="button" onClick={guardarMaquinaria} disabled={!costoMaquinaria || !descMaquinaria.trim()} className="rounded bg-finance px-3 py-1.5 text-sm text-white disabled:opacity-50">
              Agregar
            </button>
          </div>
        )}
      </div>

      <div className="mt-6">
        <h2 className="text-lg font-medium">Factura del contratista</h2>
        {orden.facturaContratista ? (
          <div className="mt-2 rounded border border-border p-3 text-sm">
            {orden.facturaContratista.tipoDocumento} {orden.facturaContratista.numeroDocumento} ({orden.facturaContratista.moneda})
          </div>
        ) : (
          orden.estado !== "Anulada" &&
          orden.contratista && (
            <div className="mt-2 flex items-end gap-2">
              <label className="text-sm">
                N° de compra (IdCompra)
                <NumberInput className="mt-1 block w-32 rounded border border-border px-2 py-1.5 text-right" value={idCompraFactura} onChange={setIdCompraFactura} maxDecimales={0} />
              </label>
              <button type="button" onClick={guardarFactura} disabled={!idCompraFactura} className="rounded bg-finance px-3 py-1.5 text-sm text-white disabled:opacity-50">
                Vincular
              </button>
            </div>
          )
        )}
      </div>

      <div className="mt-6">
        <FormularioRetiroView orden={orden} />
      </div>
    </main>
  );
}
