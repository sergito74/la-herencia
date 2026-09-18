/**
 * Catálogo de tarjetas (Historia 4) y cuenta corriente por tarjeta
 * (Historia 2) — ver specs/008-tarjetas/contracts/tarjetas-api.md.
 */

import { apiGet } from "@/services/apiClient";

export interface Tarjeta {
  idTarjeta: number;
  nombre: string;
  banco: string | null;
  activa: boolean;
}

export function fetchTarjetas(soloActivas = false): Promise<Tarjeta[]> {
  return apiGet<Tarjeta[]>("/api/tarjetas", soloActivas ? { soloActivas: "true" } : {});
}

export interface MovimientoTarjeta {
  idResumen: number;
  fecha: string | null;
  codigo: string;
  /** "Resumen" (deuda del período) o "Pago" (crédito registrado contra ese resumen). */
  origen: "Resumen" | "Pago";
  deuda: number;
  credito: number;
  saldoAcumulado: number;
}

export interface MovimientosTarjetaResponse {
  idTarjeta: number;
  tarjeta: string;
  movimientos: MovimientoTarjeta[];
}

/** Un movimiento de deuda por resumen + un movimiento de crédito por cada
 * pago registrado contra ese resumen (nunca por cuota, research.md §3). */
export function fetchMovimientosTarjeta(idTarjeta: number): Promise<MovimientosTarjetaResponse> {
  return apiGet<MovimientosTarjetaResponse>(`/api/tarjetas/${idTarjeta}/movimientos`);
}

export interface MovimientoPagoCandidato {
  origen: string;
  idMovimiento: number;
  fecha: string;
  importe: number;
  concepto: string | null;
}

/** Movimientos bancarios reales (Movimientos BNA/Galicia) ya cargados con
 * `IdContacto` apuntando a esta tarjeta, candidatos a ser el pago de un
 * resumen (punto 6 del feedback del usuario, 2026-09-19). */
export function fetchPagosCandidatos(idTarjeta: number): Promise<MovimientoPagoCandidato[]> {
  return apiGet<MovimientoPagoCandidato[]>(`/api/tarjetas/${idTarjeta}/pagos-candidatos`);
}
