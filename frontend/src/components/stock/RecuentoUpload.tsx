"use client";

import { useState } from "react";

import { aplicarRecuento, previsualizarRecuento, type EstadoRecuento, type PreviaRecuento } from "@/services/remitosApi";
import { ApiError } from "@/services/apiClient";
import { formatCantidad } from "@/lib/format";
import { filterInputClass } from "@/components/ui/FilterBar";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";

const campo = `${filterInputClass} w-full px-1.5 py-1 text-xs`;

const ESTADOS: Record<EstadoRecuento, { label: string; tone: "danger" | "success" | "neutral" | "warning" }> = {
  faltante: { label: "Faltante", tone: "danger" },
  sobrante: { label: "Sobrante", tone: "success" },
  sinDiferencia: { label: "Sin diferencia", tone: "neutral" },
  noEncontrado: { label: "No encontrado", tone: "warning" },
  ambiguo: { label: "Ambiguo", tone: "warning" },
};

const aFecha = (iso: string) => iso.split("-").reverse().join("/");

/**
 * Sube la planilla de recuento físico completada (Existencias → "Planilla de recuento
 * físico"), muestra la comparación contra el stock del sistema a la fecha del recuento
 * y, al confirmar, graba un ajuste por cada faltante o sobrante.
 */
export function RecuentoUpload({ abierto, onClose, onAplicado }: { abierto: boolean; onClose: () => void; onAplicado: () => void }) {
  const { showToast } = useToast();
  const [archivo, setArchivo] = useState<File | null>(null);
  const [fecha, setFecha] = useState("");
  const [motivo, setMotivo] = useState("");
  const [previa, setPrevia] = useState<PreviaRecuento | null>(null);
  const [soloDiferencias, setSoloDiferencias] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [trabajando, setTrabajando] = useState(false);

  function reiniciar() {
    setArchivo(null);
    setFecha("");
    setMotivo("");
    setPrevia(null);
    setError(null);
  }

  async function revisar(f: File | null = archivo, fe: string = fecha) {
    if (!f) return;
    setError(null);
    setTrabajando(true);
    try {
      const p = await previsualizarRecuento(f, fe);
      setPrevia(p);
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
      const r = await aplicarRecuento(archivo, fecha, motivo);
      showToast(`Recuento cargado: ${r.ajustes} ajustes.`, "success");
      reiniciar();
      onAplicado();
      onClose();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudieron grabar los ajustes.");
    } finally {
      setTrabajando(false);
    }
  }

  const bloqueantes = previa ? previa.resumen.noEncontrado + previa.resumen.ambiguo : 0;
  const aGrabar = previa ? previa.resumen.faltante + previa.resumen.sobrante : 0;
  const filas = previa?.renglones.filter((r) => !soloDiferencias || r.estado !== "sinDiferencia") ?? [];

  return (
    <SideDrawer open={abierto} onClose={onClose} title="Subir recuento físico" maxWidthClass="max-w-4xl">
      <p className="text-xs text-ink-secondary">
        Subí la planilla de recuento con la columna «Cantidad contada» completa. Se compara contra el stock del sistema a la fecha del recuento y, al confirmar, se graba un faltante o sobrante por cada diferencia. Los productos sin cantidad contada no se tocan.
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
              revisar(f, fecha);
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
              if (archivo && e.target.value) revisar(archivo, e.target.value);
            }}
          />
        </label>
        <label className="text-xs text-ink-secondary sm:col-span-2">
          Motivo de los ajustes
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
            {previa.sinContar > 0 && <span className="text-ink-secondary">Sin contar (no se ajustan): {previa.sinContar}</span>}
            {bloqueantes > 0 && <span className="text-status-warning">Sin identificar: {bloqueantes}</span>}
            <label className="ml-auto flex items-center gap-1 text-ink-secondary">
              <input type="checkbox" checked={soloDiferencias} onChange={(e) => setSoloDiferencias(e.target.checked)} />
              Solo diferencias
            </label>
          </div>
          <div className="max-h-[55vh] overflow-y-auto rounded-md border border-border">
            <table className="min-w-full divide-y divide-border text-xs">
              <thead className="sticky top-0 bg-surface-sunken text-left">
                <tr>
                  {["Fila", "Producto", "Unidad", `Sistema al ${aFecha(previa.fecha)}`, "Contado", "Diferencia", ""].map((h) => (
                    <th key={h} className="whitespace-nowrap px-1.5 py-1 font-medium text-ink-secondary">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filas.map((r) => (
                  <tr key={r.fila}>
                    <td className="px-1.5 py-0.5 font-data text-ink-secondary">{r.fila}</td>
                    <td className="px-1.5 py-0.5">
                      {r.producto}
                      {r.observaciones && <span className="block text-[11px] text-ink-secondary">{r.observaciones}</span>}
                    </td>
                    <td className="px-1.5 py-0.5">{r.unidadBase ?? "—"}</td>
                    <td className="px-1.5 py-0.5 text-right font-data">{r.sistema != null ? formatCantidad(r.sistema) : "—"}</td>
                    <td className="px-1.5 py-0.5 text-right font-data">{formatCantidad(r.contada)}</td>
                    <td className={`px-1.5 py-0.5 text-right font-data ${(r.diferencia ?? 0) < 0 ? "text-status-danger" : (r.diferencia ?? 0) > 0 ? "text-status-success" : ""}`}>
                      {r.diferencia != null ? `${r.diferencia > 0 ? "+" : ""}${formatCantidad(r.diferencia)}` : "—"}
                    </td>
                    <td className="px-1.5 py-0.5">
                      <StatusBadge label={ESTADOS[r.estado].label} tone={ESTADOS[r.estado].tone} />
                    </td>
                  </tr>
                ))}
                {filas.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-1.5 py-2 text-ink-secondary">
                      No hay diferencias para ajustar.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {bloqueantes > 0 && (
            <p className="text-xs text-status-warning">Hay productos que no se pudieron identificar en el catálogo: corregí el nombre en la planilla (o usá la planilla nueva desde Existencias) y volvé a subirla.</p>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded-sm border border-border px-3 py-1.5 text-xs text-ink-secondary hover:text-ink-primary">
              Cancelar
            </button>
            <button
              type="button"
              disabled={trabajando || bloqueantes > 0 || aGrabar === 0 || !motivo.trim()}
              onClick={confirmar}
              className="rounded-sm bg-finance px-3 py-1.5 text-xs text-white hover:opacity-90 disabled:opacity-40"
            >
              {trabajando ? "Grabando…" : `Confirmar ${aGrabar} ajustes`}
            </button>
          </div>
        </div>
      )}
    </SideDrawer>
  );
}
