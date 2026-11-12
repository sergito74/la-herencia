"use client";

import { useState } from "react";

import { formatCantidad } from "@/lib/format";
import type { PlanAgricolaItem } from "@/services/planificacionApi";

import { anioAgricola, hexCultivo, LOTES_PLANO, lotePlano, POLIGONOS } from "./lotesPlano";

const ANCHO = 2184;
const ALTO = 1688;

/** Plano de La Herencia (KMZ "LH Plano Lotes") con cada lote pintado por su cultivo en la campaña elegida. Si en el
 * lote hay más de un cultivo (fina + gruesa o subdivisiones distintas) se raya con los colores de cada uno. */
export function PlanoLotes({ anio, items, onLote }: {
  anio: number;
  items: PlanAgricolaItem[];
  onLote: (plano: string) => void;
}) {
  const [encima, setEncima] = useState<string | null>(null);

  const porLote = new Map<string, PlanAgricolaItem[]>();
  for (const i of items) {
    if (anioAgricola(i.campania ?? "")?.anio !== anio) continue;
    const p = lotePlano(i.numeroLote ?? "");
    if (p) porLote.set(p, [...(porLote.get(p) ?? []), i]);
  }
  const cultivosDe = (id: string) => [...new Set((porLote.get(id) ?? [])
    .sort((a, b) => Number(anioAgricola(b.campania ?? "")?.fina) - Number(anioAgricola(a.campania ?? "")?.fina))
    .map((i) => i.cultivo ?? "—"))];
  const leyenda = [...new Set([...porLote.values()].flat().map((i) => i.cultivo ?? "—"))].sort();
  const info = encima ? LOTES_PLANO.find((l) => l.id === encima) : null;

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_16rem]">
      <div className="relative overflow-hidden rounded-md border border-border bg-white">
        <svg viewBox={`60 120 ${ANCHO - 100} ${ALTO - 260}`} className="block h-auto w-full" role="img" aria-label="Plano de lotes">
          <defs>
            {LOTES_PLANO.map((l) => {
              const cs = cultivosDe(l.id);
              if (cs.length < 2) return null;
              const paso = 36;
              return (
                <pattern key={l.id} id={`mix-${l.id}`} width={paso * cs.length} height={paso * cs.length}
                  patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                  {cs.map((c, k) => <rect key={c} x={k * paso} y={0} width={paso} height={paso * cs.length} fill={hexCultivo(c)} />)}
                </pattern>
              );
            })}
          </defs>
          <image href="/plano-lotes.jpg" x={0} y={0} width={ANCHO} height={ALTO} opacity={0.35} />
          {LOTES_PLANO.map((l) => {
            const pts = POLIGONOS[l.id];
            if (!pts) return null;
            const cs = cultivosDe(l.id);
            const fill = cs.length === 0 ? "transparent" : cs.length === 1 ? hexCultivo(cs[0]) : `url(#mix-${l.id})`;
            const cx = pts.reduce((s, p) => s + p[0], 0) / pts.length;
            const cy = pts.reduce((s, p) => s + p[1], 0) / pts.length;
            const activo = encima === l.id;
            return (
              <g key={l.id} role="button" tabIndex={0} aria-label={`Lote ${l.nombre}: ${cs.join(" y ") || "sin planificar"}`}
                className="cursor-pointer outline-none"
                onMouseEnter={() => setEncima(l.id)} onMouseLeave={() => setEncima(null)}
                onFocus={() => setEncima(l.id)} onBlur={() => setEncima(null)}
                onClick={() => onLote(l.id)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onLote(l.id); } }}>
                <polygon points={pts.map((p) => p.join(",")).join(" ")} fill={fill} fillOpacity={activo ? 0.95 : 0.7}
                  stroke={activo ? "#0f172a" : "#334155"} strokeWidth={activo ? 8 : 3} />
                <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle" fontSize={44} fontWeight={700}
                  fill="#0f172a" stroke="white" strokeWidth={8} paintOrder="stroke" pointerEvents="none">
                  {l.nombre}
                </text>
                <text x={cx} y={cy + 46} textAnchor="middle" dominantBaseline="middle" fontSize={30}
                  fill="#1e293b" stroke="white" strokeWidth={6} paintOrder="stroke" pointerEvents="none">
                  {cs.join(" / ")}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <aside className="space-y-4 text-sm">
        <div className="min-h-[7rem] rounded-md border border-border bg-surface p-3">
          {info ? (
            <>
              <p className="font-semibold">Lote {info.nombre}</p>
              <p className="text-ink-secondary">{formatCantidad(info.ha)} ha según el plano</p>
              <ul className="mt-2 space-y-1">
                {(porLote.get(info.id) ?? []).map((i) => (
                  <li key={i.idPlanAgricola} className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-sm" style={{ background: hexCultivo(i.cultivo) }} aria-hidden />
                    {i.cultivo} <span className="text-ink-secondary">· {i.campania} · {i.numeroLote}</span>
                  </li>
                ))}
                {!porLote.get(info.id)?.length && <li className="text-ink-muted">Sin planificar</li>}
              </ul>
              <p className="mt-2 text-xs text-ink-secondary">Clic para ver la rotación y asignar.</p>
            </>
          ) : <p className="text-ink-secondary">Pasá el mouse por un lote para ver el detalle.</p>}
        </div>
        <div className="rounded-md border border-border bg-surface p-3">
          <p className="mb-2 font-medium">Cultivos</p>
          <ul className="space-y-1">
            {leyenda.map((c) => (
              <li key={c} className="flex items-center gap-1.5">
                <span className="h-3 w-3 rounded-sm border border-black/10" style={{ background: hexCultivo(c) }} aria-hidden />{c}
              </li>
            ))}
            <li className="flex items-center gap-1.5 text-ink-secondary">
              <span className="h-3 w-3 rounded-sm border border-black/10" style={{ background: "repeating-linear-gradient(45deg,#4ade80 0 3px,#fcd34d 3px 6px)" }} aria-hidden />
              Rayado: más de un cultivo
            </li>
          </ul>
        </div>
      </aside>
    </div>
  );
}
