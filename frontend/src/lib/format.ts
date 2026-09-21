/**
 * Formato de números y moneda de TODO el sistema (pedido explícito del
 * usuario): separador de miles ".", separador decimal ",", prefijo "$" para
 * Pesos y "us$" para Dólares, montos con 2 decimales y cantidades hasta 3.
 *
 * La agrupación se hace a mano y no con `toLocaleString`: según el navegador
 * y su configuración regional el locale es-AR no agrupa los números de 4
 * dígitos ("1234" en vez de "1.234"), y el resultado tiene que ser siempre el
 * mismo. Nunca formatear un importe o cantidad por otro camino: usar estas
 * funciones (y `MoneyInput`/`NumberInput` en los campos editables).
 */

export type MonedaFormato = "Pesos" | "Dolares";

/** Miles ".", decimales ",", sin símbolo de moneda — para celdas numéricas
 * (ej. precio unitario) donde el prefijo $ ya está implícito por contexto. */
export function formatMonto(value: number, decimales = 2): string {
  if (!Number.isFinite(value)) return "—";
  const fijo = Math.abs(value).toFixed(decimales);
  const [entero, decimal] = fijo.split(".");
  const negativo = value < 0 && Number(fijo) !== 0;
  const conMiles = entero.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${negativo ? "-" : ""}${conMiles}${decimal ? "," + decimal : ""}`;
}

/** Número sin símbolo con entre `min` y `max` decimales (los ceros de más se
 * recortan): ej. tipo de cambio (2–4), alícuotas (0–2), cantidades (0–3). */
export function formatNumero(value: number, opciones: { min?: number; max?: number } = {}): string {
  const { min = 0, max = 3 } = opciones;
  if (!Number.isFinite(value)) return "—";
  let texto = formatMonto(value, max);
  if (max > min) {
    const [entero, decimal = ""] = texto.split(",");
    let d = decimal;
    while (d.length > min && d.endsWith("0")) d = d.slice(0, -1);
    texto = d ? `${entero},${d}` : entero;
  }
  return texto;
}

/** Porcentaje a partir de una fracción (0,03 → "+3%"), con signo si `conSigno`. */
export function formatPorcentaje(fraccion: number, conSigno = false, max = 2): string {
  const texto = `${formatNumero(fraccion * 100, { max })}%`;
  return conSigno && fraccion > 0 ? `+${texto}` : texto;
}

export function formatMoneda(value: number, moneda: MonedaFormato = "Pesos"): string {
  const prefijo = moneda === "Dolares" ? "us$" : "$";
  return `${prefijo} ${formatMonto(value)}`;
}

export function formatCantidad(value: number): string {
  return formatNumero(value, { min: 0, max: 3 });
}

/** Convierte un `number` de JS a texto editable en convención local (coma
 * decimal, sin separador de miles) — ej. `60717.34` → `"60717,34"`. Usar
 * siempre esta función (nunca `String(numero)`) para precargar un input/
 * celda editable desde un valor numérico: `String()` usa punto decimal, y
 * `parseNumeroLocal` interpreta ese punto como separador de miles — el bug
 * resultante multiplica el valor por 100 al recargarlo (visto en producción
 * el 2026-09-17: 60.717,34 pasaba a 6.071.734 tras guardar y reabrir). */
export function numeroAEdicionLocal(value: number): string {
  return String(value).replace(".", ",");
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
