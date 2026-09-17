/**
 * Formato de moneda/cantidad estilo factura física (pedido explícito del
 * usuario para el módulo de Compras): separador de miles ".", separador
 * decimal "," (locale es-AR ya usa esta convención), prefijo "$" para
 * Pesos y "us$" para Dólares, montos redondeados a 2 decimales y
 * cantidades a 3 decimales.
 */

export type MonedaFormato = "Pesos" | "Dolares";

export function formatMoneda(value: number, moneda: MonedaFormato = "Pesos"): string {
  const prefijo = moneda === "Dolares" ? "us$" : "$";
  const numero = value.toLocaleString("es-AR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${prefijo} ${numero}`;
}

export function formatCantidad(value: number): string {
  return value.toLocaleString("es-AR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  });
}

/** Interpreta un texto numérico en convención local (miles ".", decimales
 * ","), tolerando también un valor ya normalizado sin separador de miles
 * (ej. "60717,34"). Usar siempre esta función para parsear celdas/inputs
 * numéricos editables — nunca `Number()`/`parseFloat` directo. */
export function parseNumeroLocal(v: string): number {
  const limpio = v.replace(/\./g, "").replace(",", ".");
  const n = Number(limpio);
  return Number.isFinite(n) ? n : 0;
}

/** Si el texto pegado viene en formato US ("60,717.34": miles "," decimales
 * "."), lo convierte a la convención local ("60717,34"). Si ya viene en
 * formato local o es ambiguo (un solo separador), lo deja igual —
 * `parseNumeroLocal` ya lo interpreta bien en ambos casos. */
export function normalizarNumeroPegado(raw: string): string {
  const t = raw.trim();
  const hasComma = t.includes(",");
  const hasDot = t.includes(".");
  if (!hasComma || !hasDot) return t;
  const esFormatoUS = t.lastIndexOf(".") > t.lastIndexOf(",");
  if (!esFormatoUS) return t; // ya es "miles . decimales ,"
  return t.replace(/,/g, "").replace(".", ",");
}
