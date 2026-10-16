"use client";

import Link from "next/link";
import { Fragment, useState } from "react";

import { aplicarRecuento, previsualizarRecuento, type AsignacionesRecuento, type EstadoRecuento, type PreviaRecuento } from "@/services/remitosApi";
import { ApiError } from "@/services/apiClient";
import { formatCantidad } from "@/lib/format";
import { filterInputClass } from "@/components/ui/FilterBar";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";
import { ProductoSelect } from "@/components/remitos/ProductoSelect";

const campo = `${filterInputClass} w-full px-1.5 py-1 text-xs`;

const ESTADOS: Record<EstadoRecuento, { label: string; tone: "danger" | "success" | "neutral" | "warning" }> = {
  faltante: { label: "Faltante", tone: "danger" },
  sobrante: { label: "Sobrante", tone: "success" },
  sinDiferencia: { label: "Sin diferencia", tone: "neutral" },
  noEncontrado: { label: "No encontrado", tone: "warning" },
  ambiguo: { label: "Ambiguo", tone: "warning" },
};

const aFecha = (iso: string) => iso.split("-").reverse().join("/");
const conSigno = (n: number) => `${n > 0 ? "+" : ""}${formatCantidad(n)}`;

/**
 * Sube la planilla de recuento físico completada y muestra cómo se reparte cada
 * diferencia entre las órdenes de trabajo del período (recuento.py): el recuento es
 * aproximado y las aplicaciones no son exactas, así que la diferencia ajusta el consumo
 * de esas órdenes y su costo llega a los lotes y cultivos.
 */
export function RecuentoUpload({ abierto, onClose, onAplicado }: { abierto: boolean; onClose: () => void; onAplicado: () => void }) {
  const { showToast } = useToast();
  const [archivo, setArchivo] = useState<File | null>(null);
  const [fecha, setFecha] = useState("");
  const [motivo, setMotivo] = useState("");
  const [previa, setPrevia] = useState<PreviaRecuento | null>(null);
  // Productos elegidos a mano (fila -> producto) para los que no se identificaron por nombre.
  const [elegidos, setElegidos] = useState<Record<number, { idProducto: number; producto: string }>>({});
  const asignaciones: AsignacionesRecuento = Object.fromEntries(Object.entries(elegidos).map(([f, p]) => [f, p.idProducto]));
  const [soloDiferencias, setSoloDiferencias] = useState(true);
  const [abiertos, setAbiertos] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [trabajando, setTrabajando] = useState(false);

  function reiniciar() {
    setArchivo(null);
    setFecha("");
    setMotivo("");
    setPrevia(null);
    setError(null);
    setAbiertos(new Set());
    setElegidos({});
  }

  async function revisar(f: File | null = archivo, fe: string = fecha, asig: AsignacionesRecuento = asignaciones) {
    if (!f) return;
    setError(null);
    setTrabajando(true);
    try {
      const p = await previsualizarRecuento(f, fe, asig);
      setPrevia(p);
      setAbiertos(new Set(p.renglones.filter((r) => r.revisar).map((r) => r.fila)));
      if (!fe) setFecha(p.fecha);
      if (!motivo) setMotivo(`Recuento físico ${aFecha(p.fecha)}`);
    } catch (e) {
      setPrevia(null);
      setError(e instanceof ApiError ? e.message : "No se pudo leer la planilla.");
    } finally {
      setTrabajando(false);
    }
  }

  async function confirmar() {
    if (!archivo || !previa) return;
    setTrabajando(true);
    try {
      const r = await aplicarRecuento(archivo, fecha, motivo, asignaciones);
      showToast(`Recuento grabado: ${r.ajustesOrden} ajustes de órdenes${r.sinImputar ? ` y ${r.sinImputar} sin imputar` : ""}.`, "success");
      reiniciar();
      onAplicado();
      onClose();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo grabar el recuento.");
    } finally {
      setTrabajando(false);
    }
  }

  function alternar(fila: number) {
    setAbiertos((prev) => {
      const s = new Set(prev);
      if (s.has(fila)) s.delete(fila);
      else s.add(fila);
      return s;
    });
  }

  const bloqueantes = previa ? previa.resumen.noEncontrado + previa.resumen.ambiguo : 0;
  const conDiferencia = previa ? previa.resumen.faltante + previa.resumen.sobrante : 0;
  const filas = previa?.renglones.filter((r) => !soloDiferencias || r.estado !== "sinDiferencia") ?? [];

  return (
    <SideDrawer open={abierto} onClose={onClose} title="Subir recuento físico" maxWidthClass="max-w-5xl">
      <p className="text-xs text-ink-secondary">
        Subí la planilla de recuento con la columna «Cantidad contada» completa. Cada diferencia contra el sistema se reparte entre las órdenes de trabajo que usaron el producto desde el recuento anterior, en proporción a lo que usó cada una: ajusta su consumo y su costo llega a los lotes y cultivos. Si no hubo órdenes en el período, queda como faltante o sobrante sin imputar. Los productos sin cantidad contada no se tocan.
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <label className="text-xs text-ink-secondary sm:col-span-3">
          Planilla completada (.xlsx)
          <input
            type="file"
            accept=".xlsx"
            className={campo}
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null;
              setArchivo(f);
              setPrevia(null);
              setElegidos({});
              revisar(f, fecha, {});
            }}
          />
        </label>
        <label className="text-xs text-ink-secondary">
          Fecha del recuento
          <input
            type="date"
            className={campo}
            value={fecha}
            onChange={(e) => {
              setFecha(e.target.value);
              if (archivo && e.target.value) revisar(archivo, e.target.value, asignaciones);
            }}
          />
        </label>
        <label className="text-xs text-ink-secondary sm:col-span-2">
          Motivo
          <input className={campo} value={motivo} maxLength={200} onChange={(e) => setMotivo(e.target.value)} />
        </label>
      </div>

      {trabajando && <p className="mt-3 text-xs text-ink-secondary">Procesando…</p>}
      {error && <p className="mt-3 text-sm text-status-danger">{error}</p>}

      {previa && (
        <div className="mt-4 space-y-2">
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className="text-status-danger">Faltantes: {previa.resumen.faltante}</span>
            <span className="text-status-success">Sobrantes: {previa.resumen.sobrante}</span>
            <span className="text-ink-secondary">Sin diferencia: {previa.resumen.sinDiferencia}</span>
            {previa.sinContar > 0 && <span className="text-ink-secondary">Sin contar: {previa.sinContar}</span>}
            {previa.aRevisar > 0 && <span className="font-medium text-status-warning">Para revisar: {previa.aRevisar}</span>}
            {bloqueantes > 0 && <span className="text-status-warning">Sin identificar: {bloqueantes}</span>}
            <label className="ml-auto flex items-center gap-1 text-ink-secondary">
              <input type="checkbox" checked={soloDiferencias} onChange={(e) => setSoloDiferencias(e.target.checked)} />
              Solo diferencias
            </label>
          </div>
          <div className="max-h-[55vh] overflow-y-auto rounded-md border border-border">
            <table className="min-w-full divide-y divide-border text-xs">
              <thead className="sticky top-0 z-10 bg-surface-sunken text-left">
                <tr>
                  {["", "Producto", "Unidad", `Sistema al ${aFecha(previa.fecha)}`, "Contado", "Diferencia", "Reparto", ""].map((h, i) => (
                    <th key={i} className="whitespace-nowrap px-1.5 py-1 font-medium text-ink-secondary">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filas.map((r) => {
                  const desplegable = r.ordenes.length > 0;
                  const abiertoFila = abiertos.has(r.fila);
                  return (
                    <Fragment key={r.fila}>
                      <tr className={r.revisar ? "bg-status-warning-bg" : undefined}>
                        <td className="w-5 px-1 text-center">
                          {desplegable && (
                            <button type="button" className="text-ink-secondary" onClick={() => alternar(r.fila)} aria-label="Ver órdenes">
                              {abiertoFila ? "▾" : "▸"}
                            </button>
                          )}
                        </td>
                        <td className="px-1.5 py-0.5">
                          {r.estado === "noEncontrado" || r.estado === "ambiguo" ? (
                            <div className="min-w-[16rem]">
                              <span className="block text-[11px] text-status-warning">
                                «{r.producto}» {r.estado === "ambiguo" ? "coincide con varios productos" : "no está en el catálogo"}: elegilo
                              </span>
                              <ProductoSelect
                                value={null}
                                placeholder="Buscar en el catálogo…"
                                onChange={(p) => {
                                  const nuevos = { ...elegidos, [r.fila]: { idProducto: p.idProducto, producto: p.producto } };
                                  setElegidos(nuevos);
                                  revisar(archivo, fecha, Object.fromEntries(Object.entries(nuevos).map(([fi, x]) => [fi, x.idProducto])));
                                }}
                              />
                            </div>
                          ) : (
                            <>
                              {r.producto}
                              {elegidos[r.fila] && <span className="ml-1 text-[11px] text-ink-secondary">(elegido a mano)</span>}
                            </>
                          )}
                          {r.observaciones && <span className="block text-[11px] text-ink-secondary">{r.observaciones}</span>}
                        </td>
                        <td className="px-1.5 py-0.5">{r.unidadBase ?? "—"}</td>
                        <td className="px-1.5 py-0.5 text-right font-data">{r.sistema != null ? formatCantidad(r.sistema) : "—"}</td>
                        <td className="px-1.5 py-0.5 text-right font-data">{formatCantidad(r.contada)}</td>
                        <td className={`px-1.5 py-0.5 text-right font-data ${(r.diferencia ?? 0) < 0 ? "text-status-danger" : (r.diferencia ?? 0) > 0 ? "text-status-success" : ""}`}>
                          {r.diferencia != null ? conSigno(r.diferencia) : "—"}
                        </td>
                        <td className="px-1.5 py-0.5 text-ink-secondary">
                          {r.estado === "faltante" || r.estado === "sobrante" ? (
                            <>
                              {r.ordenes.length > 0 && (
                                <span>
                                  {r.ordenes.length} {r.ordenes.length === 1 ? "orden" : "órdenes"}
                                  {r.porcentajeAjuste != null && <span className={r.revisar ? "font-medium text-status-warning" : ""}> ({r.porcentajeAjuste > 0 ? "+" : ""}{formatCantidad(r.porcentajeAjuste)}% del uso)</span>}
                                  {r.desde ? ` desde ${aFecha(r.desde)}` : " (desde la primera entrada)"}
                                </span>
                              )}
                              {Math.abs(r.sinImputar) > 0.005 && (
                                <span className="block font-medium text-status-warning">Sin imputar: {conSigno(r.sinImputar)} (sin órdenes en el período)</span>
                              )}
                            </>
                          ) : null}
                        </td>
                        <td className="px-1.5 py-0.5">
                          <StatusBadge label={ESTADOS[r.estado].label} tone={ESTADOS[r.estado].tone} />
                        </td>
                      </tr>
                      {abiertoFila &&
                        r.ordenes.map((o) => (
                          <tr key={`${r.fila}-${o.idOrdenInsumo}`} className="bg-surface-sunken text-ink-secondary">
                            <td />
                            <td className="px-1.5 py-0.5 pl-4" colSpan={2}>
                              <Link href={`/produccion/ordenes/${o.idOrdenTrabajo}`} target="_blank" className="text-finance underline">
                                Orden {o.idOrdenTrabajo}
                              </Link>{" "}
                              del {aFecha(o.fecha)}
                            </td>
                            <td className="px-1.5 py-0.5 text-right font-data" colSpan={2}>
                              usó {formatCantidad(o.cantidad)}
                            </td>
                            <td className="px-1.5 py-0.5 text-right font-data">{conSigno(o.ajuste)}</td>
                            <td className="px-1.5 py-0.5 font-data" colSpan={2}>
                              → {formatCantidad(o.cantidad + o.ajuste)}
                            </td>
                          </tr>
                        ))}
                    </Fragment>
                  );
                })}
                {filas.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-1.5 py-2 text-ink-secondary">
                      No hay diferencias.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {previa.aRevisar > 0 && (
            <p className="text-xs text-status-warning">
              Resaltados: el ajuste supera el 20% de lo usado en el período o no hay órdenes para repartirlo. Suele indicar una orden sin cargar o un error de conteo más que imprecisión de las aplicaciones; conviene revisarlos antes de confirmar.
            </p>
          )}
          {bloqueantes > 0 && (
            <p className="text-xs text-status-warning">Hay productos que no se pudieron identificar por su nombre: elegí cada uno en el buscador de su fila para poder confirmar.</p>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded-sm border border-border px-3 py-1.5 text-xs text-ink-secondary hover:text-ink-primary">
              Cancelar
            </button>
            <button
              type="button"
              disabled={trabajando || bloqueantes > 0 || !motivo.trim()}
              onClick={confirmar}
              className="rounded-sm bg-finance px-3 py-1.5 text-xs text-white hover:opacity-90 disabled:opacity-40"
            >
              {trabajando ? "Grabando…" : conDiferencia ? `Confirmar recuento (${conDiferencia} con diferencia)` : "Confirmar recuento"}
            </button>
          </div>
        </div>
      )}
    </SideDrawer>
  );
}
