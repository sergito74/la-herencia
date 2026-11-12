/** Lotes del plano de La Herencia (LH Plano Lotes.kmz) y a cuál pertenece cada lote del sistema. Las subdivisiones
 * (1B1, 10A1, 3AB…) se usaron en distintas campañas y caen dentro de su lote del plano (confirmado por Sergio 12/11/2026). */
export const LOTES_PLANO: { id: string; nombre: string; ha: number }[] = [
  { id: "1A", nombre: "1A", ha: 20.5 }, { id: "1B", nombre: "1B", ha: 25 }, { id: "2A", nombre: "2A", ha: 17.5 },
  { id: "2B", nombre: "2B", ha: 15 }, { id: "3A", nombre: "3A", ha: 32.1 }, { id: "3B", nombre: "3B", ha: 54.9 },
  { id: "3C", nombre: "3C", ha: 9 }, { id: "4", nombre: "4", ha: 25.2 }, { id: "5", nombre: "5", ha: 12.5 },
  { id: "6", nombre: "6", ha: 12.6 }, { id: "6A", nombre: "6A", ha: 11.7 }, { id: "6BC", nombre: "6B y C", ha: 10.1 },
  { id: "7A", nombre: "7A", ha: 12.5 }, { id: "7B", nombre: "7B", ha: 35.8 }, { id: "8A", nombre: "8A", ha: 13.5 },
  { id: "8B", nombre: "8B", ha: 14.5 }, { id: "9A", nombre: "9A", ha: 14.4 }, { id: "9B", nombre: "9B", ha: 26.5 },
  { id: "10", nombre: "10", ha: 32.6 },
];

const EXCEPCIONES: Record<string, string> = { "6B": "6BC", "6C": "6BC", "6": "6", "6A": "6A" };

/** Lote del plano al que pertenece un lote del sistema; null si no está en el plano (ej. "S/L"). */
export function lotePlano(numeroLote: string): string | null {
  const n = numeroLote.trim().toUpperCase();
  if (EXCEPCIONES[n]) return EXCEPCIONES[n];
  if (/^10/.test(n)) return "10";
  if (/^[5]/.test(n)) return "5";
  const m = n.match(/^(\d)([A-C])?/);
  if (!m) return null;
  const id = m[1] + (m[2] ?? "");
  return LOTES_PLANO.some((l) => l.id === id) ? id : LOTES_PLANO.some((l) => l.id === m[1]) ? m[1] : null;
}

/** Color fijo por cultivo (siempre acompañado del nombre). */
export function colorCultivo(cultivo: string | null | undefined): string {
  const c = (cultivo ?? "").toLowerCase();
  if (c.includes("soja") && c.includes("segunda")) return "bg-lime-100 text-lime-900 border-lime-300";
  if (c.includes("soja")) return "bg-green-200 text-green-900 border-green-400";
  if (c.includes("diferido")) return "bg-orange-100 text-orange-900 border-orange-300";
  if (c.includes("maiz") || c.includes("maíz")) return "bg-yellow-200 text-yellow-900 border-yellow-400";
  if (c.includes("trigo")) return "bg-amber-100 text-amber-900 border-amber-300";
  if (c.includes("cebada")) return "bg-stone-200 text-stone-800 border-stone-400";
  if (c.includes("avena")) return "bg-sky-100 text-sky-900 border-sky-300";
  if (c.includes("sorgo")) return "bg-rose-100 text-rose-900 border-rose-300";
  if (c.includes("girasol")) return "bg-amber-300 text-amber-950 border-amber-500";
  if (c.includes("pastura")) return "bg-teal-100 text-teal-900 border-teal-300";
  return "bg-slate-100 text-slate-800 border-slate-300";
}

/** Año agrícola de una campaña: "2025/2026" (gruesa) y "2025" (fina) caen en la misma columna 25/26. */
export function anioAgricola(nombre: string): { anio: number; fina: boolean } | null {
  const m = nombre.match(/^(\d{4})/);
  return m ? { anio: Number(m[1]), fina: !nombre.includes("/") } : null;
}
