/** 039: formato y etiquetas compartidas de pastaje (regla global: miles '.', decimales ','). */

import type { BadgeTone } from "@/components/ui/StatusBadge";
import { formatMoneda, formatNumero } from "@/lib/format";
import type { TipoMovimiento, TipoTarifa } from "@/services/pastajeApi";

export const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

export const pesos = (v: string | number | null | undefined, moneda: "ARS" | "USD" | string = "ARS") =>
  v === null || v === undefined || v === "" ? "—" : formatMoneda(Number(v), moneda === "USD" ? "Dolares" : "Pesos");
export const kg = (v: string | number | null | undefined) => (v === null || v === undefined ? "—" : `${formatNumero(Number(v), { min: 0, max: 2 })} kg`);
export const indice = (v: string | number | null | undefined) => (v === null || v === undefined ? "—" : formatMoneda(Number(v), "Pesos"));

export function mesTexto(periodo: string): string {
  const [a, m] = periodo.split("-");
  return `${MESES[Number(m) - 1]} ${a}`;
}

export function tarifaTexto(t: { tipoTarifa: TipoTarifa; valor: string }): string {
  if (t.tipoTarifa === "kg_novillo") return `${formatNumero(Number(t.valor), { max: 2 })} kg de novillo / cab / mes`;
  return `${formatMoneda(Number(t.valor), t.tipoTarifa === "fijo_usd" ? "Dolares" : "Pesos")} / cab / mes`;
}

export const ETIQUETA_MOV: Record<TipoMovimiento, string> = {
  ingreso: "Ingreso",
  egreso: "Egreso",
  muerte: "Muerte",
  faltante: "Faltante",
  nacimiento: "Nacimiento",
  destete: "Destete",
  recuento: "Recuento",
};

export function tonoEstadoMes(estado: string): BadgeTone {
  if (estado === "Cobrado") return "success";
  if (estado === "Sin liquidar" || estado === "Liquidado sin factura") return "danger";
  if (estado === "En curso" || estado === "Sin hacienda") return "neutral";
  return "warning";
}

export const tonoContrato = (e: string): BadgeTone => (e === "vigente" ? "success" : e === "anulado" ? "danger" : "neutral");

export const inputCls = "mt-1 block w-full rounded-sm border border-border bg-surface px-3 py-2 text-sm";
export const btnPrimario = "rounded-sm bg-agro px-4 py-2 text-sm text-white hover:opacity-90 disabled:opacity-50";
export const btnSecundario = "rounded-sm border border-border px-3 py-1.5 text-sm hover:bg-surface-muted disabled:opacity-50";
