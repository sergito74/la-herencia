import type { FiltrosComprasResponse } from "@/services/comprasApi";

/** Campañas que admite una línea según su destino y el plan agrícola (036). Sin destino rige "General".
 * Si la línea ya tenía una campaña que hoy no está en el plan (compra vieja), se sigue mostrando para no perderla. */
export function campaniasParaDestino(
  filtros: FiltrosComprasResponse | undefined,
  destino: string,
  actual: string,
): string[] {
  const nombreDestino = destino.trim() || "General";
  const idDestino = filtros?.destinos.find((d) => (d.destino ?? "").trim().toLowerCase() === nombreDestino.toLowerCase())?.idDestino;
  const ids = idDestino !== undefined ? filtros?.campañasPorDestino?.[String(idDestino)] : undefined;
  const todas = (filtros?.campañas ?? []).filter((c) => c.campania);
  const validas = ids ? todas.filter((c) => ids.includes(c.idCampania)) : todas;
  const nombres = validas.map((c) => c.campania as string);
  if (actual && !nombres.includes(actual)) nombres.unshift(actual);
  return nombres;
}
