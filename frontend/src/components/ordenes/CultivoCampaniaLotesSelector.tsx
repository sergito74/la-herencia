"use client";

import Link from "next/link";
import { useState } from "react";

import { CultivoChip } from "@/components/cultivos/CultivoChip";
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
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <label className="block text-sm">
          <select aria-label="Cultivo" className="rounded border border-border px-2 py-1" value={nuevoCultivo ?? ""} onChange={(e) => setNuevoCultivo(Number(e.target.value) || null)}>
            <option value="">Cultivo…</option>
            {cultivos.map((c) => (
              <option key={c.idCultivo} value={c.idCultivo}>
                {c.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <select aria-label="Campaña" className="rounded border border-border px-2 py-1" value={nuevaCampania ?? ""} onChange={(e) => setNuevaCampania(Number(e.target.value) || null)}>
            <option value="">Campaña…</option>
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
          className="rounded border border-border px-3 py-1 text-sm hover:bg-surface-sunken disabled:opacity-50"
        >
          + Agregar
        </button>

        {grupos.length > 0 && (
          <span className="ml-auto text-sm font-medium">Total: <span className="font-data">{formatCantidad(superficieTotal)}</span> ha</span>
        )}
      </div>
      {grupos.length === 0 && <p className="text-sm text-ink-secondary">Agregá al menos un Cultivo/Campaña para elegir sus lotes.</p>}

      {grupos.map((g, i) => (
        <div key={`${g.idCultivo}-${g.idCampania}`} className="rounded border border-border px-3 py-2">
          <div className="mb-1 flex flex-wrap items-center gap-3 text-sm">
            <CultivoChip cultivo={g.cultivo} />
            <span className="font-medium">{g.campania}</span>
            <span className="text-ink-secondary"><span className="font-data">{formatCantidad(superficieGrupo(g))}</span> ha incluidas</span>
            {g.lotes.length > 0 && (
              <>
                <button type="button" onClick={() => alternarTodos(i, true)} className="text-finance hover:underline">Todos</button>
                <button type="button" onClick={() => alternarTodos(i, false)} className="text-finance hover:underline">Ninguno</button>
              </>
            )}
            <button type="button" onClick={() => quitarGrupo(i)} title="Quitar Cultivo/Campaña" aria-label="Quitar Cultivo/Campaña"
              className="ml-auto flex h-6 w-6 items-center justify-center rounded text-status-danger hover:bg-status-danger-bg">
              ✕
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
              <div className="flex flex-wrap gap-1.5">
                {g.lotes.map((l) => (
                  <label key={l.idLote}
                    className={`flex cursor-pointer items-center gap-1 rounded border px-1.5 py-0.5 text-xs ${l.incluido ? "border-finance/50 bg-finance/5" : "border-border text-ink-muted"}`}>
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

    </div>
  );
}
