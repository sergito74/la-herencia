"use client";

import { useMemo, useState } from "react";

import { formatCantidad } from "@/lib/format";
import { ApiError } from "@/services/apiClient";
import type { Campania, Cultivo, Lote } from "@/services/ordenesApi";
import { crearPlanAgricola, eliminarPlanAgricola, type PlanAgricolaItem } from "@/services/planificacionApi";
import { useToast } from "@/components/ui/Toast";

/**
 * Administración de la Planificación Agrícola (qué lote se destina a qué
 * Cultivo/Campaña, según lo definido con los asesores). Un mismo lote puede
 * tener más de un Cultivo en la misma Campaña (double crop).
 */
export function PlanificacionAgricolaListado({
  items,
  lotes,
  cultivos,
  campanias,
  onCambio,
}: {
  items: PlanAgricolaItem[];
  lotes: Lote[];
  cultivos: Cultivo[];
  campanias: Campania[];
  onCambio: () => void;
}) {
  const { showToast } = useToast();
  const [idCampaniaFiltro, setIdCampaniaFiltro] = useState<number | null>(campanias[0]?.idCampania ?? null);
  const [idLote, setIdLote] = useState<number | null>(null);
  const [idCultivo, setIdCultivo] = useState<number | null>(null);
  const [idCampania, setIdCampania] = useState<number | null>(idCampaniaFiltro);
  const [guardando, setGuardando] = useState(false);

  const filtrados = useMemo(
    () => (idCampaniaFiltro ? items.filter((i) => i.idCampania === idCampaniaFiltro) : items),
    [items, idCampaniaFiltro]
  );

  const superficieTotal = filtrados.reduce((acc, i) => acc + (i.superficie ?? 0), 0);
  const porCultivo = useMemo(() => {
    const mapa = new Map<string, number>();
    for (const i of filtrados) mapa.set(i.cultivo ?? "—", (mapa.get(i.cultivo ?? "—") ?? 0) + (i.superficie ?? 0));
    return [...mapa.entries()];
  }, [filtrados]);

  async function agregar() {
    if (!idLote || !idCultivo || !idCampania) return;
    setGuardando(true);
    try {
      await crearPlanAgricola({ idLote, idCultivo, idCampania });
      showToast("Lote asignado.", "success");
      setIdLote(null);
      setIdCultivo(null);
      onCambio();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo asignar el lote.", "danger");
    } finally {
      setGuardando(false);
    }
  }

  async function quitar(id: number) {
    try {
      await eliminarPlanAgricola(id);
      showToast("Asignación eliminada.", "success");
      onCambio();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo eliminar.", "danger");
    }
  }

  return (
    <div className="space-y-4">
      <label className="block text-sm">
        Campaña
        <select
          className="mt-1 rounded border border-border px-2 py-1.5"
          value={idCampaniaFiltro ?? ""}
          onChange={(e) => setIdCampaniaFiltro(Number(e.target.value) || null)}
        >
          <option value="">Todas</option>
          {campanias.map((c) => (
            <option key={c.idCampania} value={c.idCampania}>
              {c.nombre}
            </option>
          ))}
        </select>
      </label>

      <div className="rounded border border-border p-3">
        <h2 className="mb-2 font-medium">Nueva asignación</h2>
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-sm">
            Lote
            <select className="mt-1 block rounded border border-border px-2 py-1.5" value={idLote ?? ""} onChange={(e) => setIdLote(Number(e.target.value) || null)}>
              <option value="">Elegí…</option>
              {lotes.map((l) => (
                <option key={l.idLote} value={l.idLote}>
                  {l.numeroLote} ({formatCantidad(l.superficie)} ha)
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            Cultivo / destino
            <select className="mt-1 block rounded border border-border px-2 py-1.5" value={idCultivo ?? ""} onChange={(e) => setIdCultivo(Number(e.target.value) || null)}>
              <option value="">Elegí…</option>
              {cultivos.map((c) => (
                <option key={c.idCultivo} value={c.idCultivo}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            Campaña
            <select className="mt-1 block rounded border border-border px-2 py-1.5" value={idCampania ?? ""} onChange={(e) => setIdCampania(Number(e.target.value) || null)}>
              <option value="">Elegí…</option>
              {campanias.map((c) => (
                <option key={c.idCampania} value={c.idCampania}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={agregar}
            disabled={guardando || !idLote || !idCultivo || !idCampania}
            className="rounded bg-finance px-3 py-1.5 text-sm text-white disabled:opacity-50"
          >
            Agregar
          </button>
        </div>
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-ink-secondary">
            <th className="py-1">Lote</th>
            <th className="py-1">Superficie</th>
            <th className="py-1">Cultivo / destino</th>
            <th className="py-1">Campaña</th>
            <th className="py-1" />
          </tr>
        </thead>
        <tbody>
          {filtrados.map((i) => (
            <tr key={i.idPlanAgricola} className="border-b border-border">
              <td className="py-1">{i.numeroLote}</td>
              <td className="py-1">{formatCantidad(i.superficie ?? 0)}</td>
              <td className="py-1">{i.cultivo}</td>
              <td className="py-1">{i.campania}</td>
              <td className="py-1">
                <button type="button" onClick={() => quitar(i.idPlanAgricola)} className="text-status-danger hover:underline">
                  Quitar
                </button>
              </td>
            </tr>
          ))}
          {filtrados.length === 0 && (
            <tr>
              <td colSpan={5} className="py-3 text-center text-ink-secondary">
                Sin asignaciones para esta campaña.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <div className="rounded border border-border bg-surface-sunken p-3 text-sm">
        <p className="font-medium">Superficie total: {formatCantidad(superficieTotal)} ha</p>
        <ul className="ml-4 list-disc text-ink-secondary">
          {porCultivo.map(([cultivo, sup]) => (
            <li key={cultivo}>
              {cultivo}: {formatCantidad(sup)} ha
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
