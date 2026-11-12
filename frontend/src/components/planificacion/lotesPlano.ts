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

/** Color de relleno por cultivo para el plano y las barras (mismo criterio que colorCultivo). */
export function hexCultivo(cultivo: string | null | undefined): string {
  const c = (cultivo ?? "").toLowerCase();
  if (c.includes("soja") && c.includes("segunda")) return "#bef264";
  if (c.includes("soja")) return "#4ade80";
  if (c.includes("diferido")) return "#fdba74";
  if (c.includes("maiz") || c.includes("maíz")) return "#facc15";
  if (c.includes("trigo")) return "#fcd34d";
  if (c.includes("cebada")) return "#a8a29e";
  if (c.includes("avena")) return "#7dd3fc";
  if (c.includes("sorgo")) return "#fda4af";
  if (c.includes("girasol")) return "#f59e0b";
  if (c.includes("pastura")) return "#5eead4";
  return "#cbd5e1";
}

/** Contorno de cada lote sobre la imagen del plano (public/plano-lotes.jpg, coordenadas 2184×1688). */
export const POLIGONOS: Record<string, [number, number][]> = {
  "1A": [[150, 148], [895, 155], [905, 323], [125, 283]],
  "1B": [[125, 283], [905, 323], [920, 520], [125, 455], [98, 432]],
  "4": [[895, 155], [1258, 158], [1280, 550], [920, 520]],
  "7B": [[1258, 158], [1700, 158], [1700, 612], [1285, 608], [1280, 550]],
  "9B": [[1700, 158], [2060, 158], [2060, 565], [1700, 548]],
  "9A": [[1700, 548], [2060, 565], [2060, 780], [1712, 795], [1690, 790], [1690, 612]],
  "7A": [[1285, 608], [1690, 612], [1690, 780], [1675, 790], [1297, 805]],
  "5": [[997, 528], [1280, 550], [1297, 805], [1085, 812], [1080, 735], [1010, 740]],
  "2B": [[140, 470], [893, 535], [895, 600], [800, 573], [710, 566], [400, 697], [165, 550]],
  "2A": [[400, 697], [710, 566], [800, 573], [895, 600], [905, 825], [605, 825]],
  "3C": [[88, 477], [120, 512], [130, 578], [522, 818], [92, 805]],
  "3B": [[92, 820], [535, 822], [668, 898], [645, 1358], [96, 1372]],
  "3A": [[668, 898], [1420, 1338], [645, 1358]],
  "6BC": [[605, 825], [1072, 825], [1088, 832], [1040, 1067]],
  "6A": [[1088, 832], [1420, 812], [1420, 845], [1140, 1127], [1040, 1067]],
  "6": [[1140, 1127], [1420, 845], [1445, 1307]],
  "8A": [[1420, 812], [1708, 798], [1725, 1065], [1435, 1090]],
  "8B": [[1435, 1090], [1725, 1065], [1742, 1328], [1490, 1335], [1445, 1307]],
  "10": [[1712, 795], [2060, 780], [2060, 1322], [1742, 1328]],
};
