import type { DistribucionIn } from "@/services/ordenesApi";

/**
 * Espejo en el cliente de `distribucion.repartir_total` (backend): reparte
 * `cantidadTotal` entre los lotes en proporción al peso dosis×superficie de
 * cada uno — solo para la previsualización en vivo del formulario; el cálculo
 * que se guarda siempre lo hace el backend al confirmar.
 */
export function repartirTotal(cantidadTotal: number, distribuciones: DistribucionIn[]): number[] {
  const pesos = distribuciones.map((d) => (d.aplicar ? d.dosisHa * d.superficie : 0));
  const pesoTotal = pesos.reduce((a, b) => a + b, 0);
  if (pesoTotal <= 0) return pesos.map(() => 0);
  return pesos.map((p) => Math.round(((cantidadTotal * p) / pesoTotal) * 10000) / 10000);
}
