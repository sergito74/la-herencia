"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { Button, ButtonLink } from "@/components/ui/Button";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { LoadingState, ErrorState } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";
import { formatCantidad, formatFecha, formatMoneda } from "@/lib/format";
import { aprobarCorridas, fetchDocumentoDetalle, type DocumentoFila, type FraccionDetalle } from "@/services/imputacionDocumentosApi";
import { ChipDestino } from "./ChipsDestino";
import { TONO_ESTADO } from "./estadoDocumento";

const ESTADO_FRACCION: Record<FraccionDetalle["estado"], { texto: string; tono: "success" | "warning" }> = {
  Aprobada: { texto: "Aprobado", tono: "success" },
  Pendiente: { texto: "Pendiente", tono: "warning" },
  RequiereIntervencion: { texto: "Requiere tu decisión", tono: "warning" },
};

/** Detalle de un documento en el panel lateral (auditoría de diseño 18/11/2026): a dónde fue cada peso, lo cargado en la
 * compra frente a lo que calculó el sistema, y las acciones, sin salir del listado. */
export function DocumentoDrawer({ fila, onClose }: { fila: DocumentoFila | null; onClose: () => void }) {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const det = useQuery({ queryKey: ["imputacion-doc", fila?.idCompra], queryFn: () => fetchDocumentoDetalle(fila!.idCompra), enabled: !!fila });
  const aprobar = useMutation({
    mutationFn: (ids: string[]) => aprobarCorridas(ids),
    onSuccess: (r) => {
      showToast(r.fallidas ? `Se aprobaron ${r.aprobadas}; ${r.fallidas} cambiaron y hay que revisarlas.` : "Imputación aprobada.", r.fallidas ? "neutral" : "success");
      qc.invalidateQueries({ queryKey: ["imputacion-docs"] });
      qc.invalidateQueries({ queryKey: ["imputacion-doc", fila?.idCompra] });
    },
    onError: () => showToast("No se pudo aprobar.", "danger"),
  });
  if (!fila) return null;
  const d = det.data;
  const pendientes = [...new Set((d?.lineas ?? []).flatMap((l) => l.fracciones.filter((f) => f.estado === "Pendiente").map((f) => f.idCorrida)))];
  const moneda = fila.moneda === "Dolares" ? "Dolares" : "Pesos";

  return (
    <SideDrawer open onClose={onClose} maxWidthClass="max-w-2xl" verCompleto={`/compras/${fila.idCompra}/editar`}
      title={`${fila.tipoDocumento ?? "Documento"} ${fila.numeroDocumento ?? ""} · ${fila.proveedor ?? ""}`}
      subtitulo={<span className="flex items-center gap-2">{formatFecha(fila.fecha)} <StatusBadge label={fila.estadoTexto} tone={TONO_ESTADO[fila.estado]} /></span>}>
      <div className="space-y-5 text-sm">
        <div>
          <p className="font-data text-2xl font-semibold text-ink-primary">{formatMoneda(fila.importe)}</p>
          <p className="text-xs text-ink-secondary">imputado a costos{moneda === "Dolares" ? " (en pesos, al tipo de cambio del comprobante)" : ""}</p>
          {fila.motivo && <p className="mt-2 rounded-md bg-status-warning-bg px-3 py-2 text-status-warning">{fila.motivo}</p>}
        </div>

        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">A dónde fue</h3>
          {!fila.destinos.length ? <p className="text-ink-secondary">Este documento no se imputa a costos (impuestos, parte particular o financiero).</p> : (
            <ul className="space-y-2">
              {fila.destinos.map((x) => (
                <li key={x.clave}>
                  <div className="flex items-center justify-between gap-3">
                    <ChipDestino d={x} />
                    <span className="font-data">{formatMoneda(x.importe)}{x.porcentaje != null && <span className="ml-2 text-xs text-ink-muted">{x.porcentaje}%</span>}</span>
                  </div>
                  <div className="mt-1 h-1.5 rounded-full bg-surface-sunken"><div className="h-1.5 rounded-full bg-ink-muted/50" style={{ width: `${Math.min(100, Math.abs(x.porcentaje ?? 100))}%` }} /></div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">Renglones · cargado en la compra y calculado por el sistema</h3>
          {det.isLoading ? <LoadingState rows={3} /> : det.isError ? <ErrorState message="No se pudo leer el detalle." /> : (
            <ul className="divide-y divide-border rounded-md border border-border">
              {d?.lineas.map((l) => {
                const cargado = l.campaniaManual && l.campaniaManual !== "No Aplica" ? l.campaniaManual : l.centroCostoManual ?? l.rubroManual ?? "—";
                return (
                  <li key={l.idDetalleCompra} className="space-y-1 px-3 py-2">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="font-medium">{l.producto}</span>
                      <span className="font-data text-ink-secondary">{l.cantidad != null ? `${formatCantidad(l.cantidad)} ${l.unidad ?? ""}` : ""}</span>
                    </div>
                    <p className="text-xs text-ink-secondary">Cargado: {cargado}{l.rubroManual && cargado !== l.rubroManual ? ` · ${l.rubroManual}` : ""}</p>
                    {l.fracciones.length ? (
                      <ul className="space-y-0.5 text-xs">
                        {l.fracciones.map((f) => (
                          <li key={f.idPropuesta} className="flex flex-wrap items-center justify-between gap-2">
                            <span>→ {f.destino}{f.lote ? ` · lote ${f.lote}` : ""}{f.cantidad != null && f.origen !== "Contratista" ? ` · ${formatCantidad(f.cantidad)} ${f.unidad ?? ""}` : ""}</span>
                            <span className="flex items-center gap-2"><span className="font-data">{formatMoneda(f.importe)}</span>
                              {f.estado !== "Aprobada" && <StatusBadge label={ESTADO_FRACCION[f.estado].texto} tone={ESTADO_FRACCION[f.estado].tono} />}</span>
                          </li>
                        ))}
                      </ul>
                    ) : <p className="text-xs text-ink-muted">{l.enRepartoOrdenes ? "Su costo llega por el reparto de las órdenes de trabajo." : "No se imputa a costos."}</p>}
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <div className="flex flex-wrap gap-2 border-t border-border pt-4">
          {pendientes.length > 0 && <SoloLectura><Button variant="primary" disabled={aprobar.isPending} onClick={() => aprobar.mutate(pendientes)}>
            {aprobar.isPending ? "Aprobando…" : "Aprobar"}</Button></SoloLectura>}
          <ButtonLink href={`/compras/${fila.idCompra}/editar`}>Abrir la compra para corregir</ButtonLink>
        </div>
      </div>
    </SideDrawer>
  );
}
