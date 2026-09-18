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
  deuda: number;
  credito: number;
  saldoAcumulado: number;
}

export interface MovimientosTarjetaResponse {
  idTarjeta: number;
  tarjeta: string;
  movimientos: MovimientoTarjeta[];
}

/** Un movimiento por resumen (nunca por cuota, research.md §3). */
export function fetchMovimientosTarjeta(idTarjeta: number): Promise<MovimientosTarjetaResponse> {
  return apiGet<MovimientosTarjetaResponse>(`/api/tarjetas/${idTarjeta}/movimientos`);
}
