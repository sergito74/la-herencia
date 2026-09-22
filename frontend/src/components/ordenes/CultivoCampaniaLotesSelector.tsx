"use client";

import Link from "next/link";
import { useState } from "react";

import { formatCantidad } from "@/lib/format";
import type { Campania, Cultivo, PlanAgricolaItem } from "@/services/ordenesApi";

export interface LoteDeGrupo {
  idLote: number;
  numeroLote: string;
  superficie: number;
  incluido: boolean;
  fueraDelPlan?: boolean;
}

export interface GrupoCultivoCampania {
  idCultivo: number;
  idCampania: number;
  cultivo: string;
  campania: string;
  lotes: LoteDeGrupo[];
}

export interface LoteBase {
  idLote: number;
  idCultivo: number;
  idCampania: number;
  superficie: number;
}

/** Lotes efectivamente incluidos, aplanados — la base que comparten todos los
 * renglones de insumo de la orden (cada uno pide dosis/ha sobre este mismo set). */
export function lotesBaseDeGrupos(grupos: GrupoCultivoCampania[]): LoteBase[] {
  return grupos.flatMap((g) =>
    g.lotes.filter((l) => l.incluido).map((l) => ({ idLote: l.idLote, idCultivo: g.idCultivo, idCampania: g.idCampania, superficie: l.superficie }))
  );
}

/**
 * Selección de Cultivo/Campaña con sus lotes, a nivel de la orden completa
 * (no por renglón): el ingeniero agronómico elige uno o más Cultivo/Campaña,
 * los lotes se sugieren desde la Planificación Agrícola (qué lote se destinó a
 * qué Cultivo, definido con los asesores) y puede incluir todos o excluir
 * alguno puntual antes de cargar los insumos.
 */
export function CultivoCampaniaLotesSelector({
  cultivos,
  campanias,
  planAgricola,
  grupos,
  onChange,
}: {
  cultivos: Cultivo[];
  campanias: Campania[];
  planAgricola: PlanAgricolaItem[];
  grupos: GrupoCultivoCampania[];
  onChange: (grupos: GrupoCultivoCampania[]) => void;
}) {
  const [nuevoCultivo, setNuevoCultivo] = useState<number | null>(null);
  const [nuevaCampania, setNuevaCampania] = useState<number | null>(null);

  const agregarGrupo = () => {
    if (!nuevoCultivo || !nuevaCampania) return;
    if (grupos.some((g) => g.idCultivo === nuevoCultivo && g.idCampania === nuevaCampania)) return;
    const cultivo = cultivos.find((c) => c.idCultivo === nuevoCultivo)?.nombre ?? "";
    const campania = campanias.find((c) => c.idCampania === nuevaCampania)?.nombre ?? "";
    const lotes = planAgricola
      .filter((p) => p.idCultivo === nuevoCultivo && p.idCampania === nuevaCampania)
      .map((p) => ({ idLote: p.idLote, numeroLote: p.numeroLote ?? String(p.idLote), superficie: p.superficie ?? 0, incluido: true }));
    onChange([...grupos, { idCultivo: nuevoCultivo, idCampania: nuevaCampania, cultivo, campania, lotes }]);
    setNuevoCultivo(null);
    setNuevaCampania(null);
  };

  const quitarGrupo = (i: number) => onChange(grupos.filter((_, idx) => idx !== i));

  const alternarLote = (i: number, idLote: number, incluido: boolean) => {
    const copia = [...grupos];
    copia[i] = { ...copia[i], lotes: copia[i].lotes.map((l) => (l.idLote === idLote ? { ...l, incluido } : l)) };
    onChange(copia);
  };

  const alternarTodos = (i: number, incluido: boolean) => {
    const copia = [...grupos];
    copia[i] = { ...copia[i], lotes: copia[i].lotes.map((l) => ({ ...l, incluido })) };
    onChange(copia);
  };

  const superficieGrupo = (g: GrupoCultivoCampania) => g.lotes.filter((l) => l.incluido).reduce((acc, l) => acc + l.superficie, 0);
  const superficieTotal = grupos.reduce((acc, g) => acc + superficieGrupo(g), 0);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-2">
        <label className="block text-sm">
          Cultivo
          <select className="mt-1 rounded border border-border px-2 py-1.5" value={nuevoCultivo ?? ""} onChange={(e) => setNuevoCultivo(Number(e.target.value) || null)}>
            <option value="">Elegí…</option>
            {cultivos.map((c) => (
              <option key={c.idCultivo} value={c.idCultivo}>
                {c.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          Campaña
          <select className="mt-1 rounded border border-border px-2 py-1.5" value={nuevaCampania ?? ""} onChange={(e) => setNuevaCampania(Number(e.target.value) || null)}>
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
          onClick={agregarGrupo}
          disabled={!nuevoCultivo || !nuevaCampania}
          className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken disabled:opacity-50"
        >
          + Agregar Cultivo/Campaña
        </button>
      </div>

      {grupos.length === 0 && <p className="text-sm text-ink-secondary">Agregá al menos un Cultivo/Campaña para elegir sus lotes.</p>}

      {grupos.map((g, i) => (
        <div key={`${g.idCultivo}-${g.idCampania}`} className="rounded border border-border p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="font-medium">
              {g.cultivo} — {g.campania}
              <span className="ml-2 text-sm font-normal text-ink-secondary">{formatCantidad(superficieGrupo(g))} ha incluidas</span>
            </span>
            <button type="button" onClick={() => quitarGrupo(i)} className="text-status-danger hover:underline">
              Quitar grupo
            </button>
          </div>
          {g.lotes.length === 0 ? (
            <p className="text-sm text-ink-secondary">
              No hay lotes planificados para este Cultivo/Campaña.{" "}
              <Link href="/produccion/planificacion" className="underline">
                Cargarlos en Planificación Agrícola
              </Link>
              .
            </p>
          ) : (
            <>
              <div className="mb-1 flex gap-3 text-sm">
                <button type="button" onClick={() => alternarTodos(i, true)} className="text-finance hover:underline">
                  Todos
                </button>
                <button type="button" onClick={() => alternarTodos(i, false)} className="text-finance hover:underline">
                  Ninguno
                </button>
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1">
                {g.lotes.map((l) => (
                  <label key={l.idLote} className="flex items-center gap-1 text-sm">
                    <input type="checkbox" checked={l.incluido} onChange={(e) => alternarLote(i, l.idLote, e.target.checked)} />
                    {l.numeroLote} ({formatCantidad(l.superficie)} ha)
                    {l.fueraDelPlan && <span className="text-status-warning">· fuera del plan</span>}
                  </label>
                ))}
              </div>
            </>
          )}
        </div>
      ))}

      {grupos.length > 0 && (
        <p className="text-sm font-medium">Superficie total afectada: {formatCantidad(superficieTotal)} ha</p>
      )}
    </div>
  );
}
