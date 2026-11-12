/** Código de colores de los cultivos (12/11/2026): el mismo color en toda la aplicación, siempre con el nombre escrito. */
const PALETA: { prueba: (c: string) => boolean; hex: string; clases: string }[] = [
  { prueba: (c) => c.includes("soja") && c.includes("segunda"), hex: "#bef264", clases: "bg-lime-100 text-lime-900 border-lime-300" },
  { prueba: (c) => c.includes("soja"), hex: "#4ade80", clases: "bg-green-200 text-green-900 border-green-400" },
  { prueba: (c) => c.includes("diferido"), hex: "#fdba74", clases: "bg-orange-100 text-orange-900 border-orange-300" },
  { prueba: (c) => c.includes("maiz") || c.includes("maíz"), hex: "#facc15", clases: "bg-yellow-200 text-yellow-900 border-yellow-400" },
  { prueba: (c) => c.includes("trigo"), hex: "#fcd34d", clases: "bg-amber-100 text-amber-900 border-amber-300" },
  { prueba: (c) => c.includes("cebada"), hex: "#a8a29e", clases: "bg-stone-200 text-stone-800 border-stone-400" },
  { prueba: (c) => c.includes("avena"), hex: "#7dd3fc", clases: "bg-sky-100 text-sky-900 border-sky-300" },
  { prueba: (c) => c.includes("sorgo"), hex: "#fda4af", clases: "bg-rose-100 text-rose-900 border-rose-300" },
  { prueba: (c) => c.includes("girasol"), hex: "#f59e0b", clases: "bg-amber-300 text-amber-950 border-amber-500" },
  { prueba: (c) => c.includes("pastura"), hex: "#5eead4", clases: "bg-teal-100 text-teal-900 border-teal-300" },
];
const NEUTRO = { hex: "#cbd5e1", clases: "bg-slate-100 text-slate-800 border-slate-300" };

const buscar = (cultivo: string | null | undefined) => {
  const c = (cultivo ?? "").toLowerCase();
  return PALETA.find((p) => p.prueba(c)) ?? NEUTRO;
};

/** Clases Tailwind (fondo, texto, borde) del cultivo. */
export const colorCultivo = (cultivo: string | null | undefined) => buscar(cultivo).clases;
/** Color de relleno del cultivo (barras, plano, gráficos). */
export const hexCultivo = (cultivo: string | null | undefined) => buscar(cultivo).hex;
