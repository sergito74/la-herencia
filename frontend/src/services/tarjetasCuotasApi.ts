/**
 * Compras en cuotas (Historia 3) — **solo lectura** desde 2026-09-19
 * (feedback del usuario, punto 5): la estructura real es obsoleta, sin
 * uso desde diciembre de 2015 (ver backend/src/features/tarjetas_cuotas/
 * repository.py). Se conserva como catálogo histórico de referencia.
 */

import { apiGet } from "@/services/apiClient";

export interface Cuota {
  idCuota: number;
  numeroCuota: number;
  fechaVencimiento: string;
  importe: number;
  cobrado: boolean;
}

export interface CompraCuotasDetalle {
  idPagoTarjeta: number;
  idContacto: number;
  contacto: string | null;
  fecha: string;
  nroComprobante: number;
  cantidadCuotas: number;
  importeTotal: number;
  cuotas: Cuota[];
}

export interface CompraCuotasListItem {
  idPagoTarjeta: number;
  idContacto: number;
  contacto: string | null;
  fecha: string;
  nroComprobante: number;
  cantidadCuotas: number;
  cuotasCobradas: number;
  cuotasPendientes: number;
}

export interface ComprasCuotasListResponse {
  items: CompraCuotasListItem[];
  page: number;
  pageSize: number;
  total: number;
}

export function fetchCompras(params: {
  idContacto?: number;
  fechaDesde?: string;
  fechaHasta?: string;
  page?: number;
  pageSize?: number;
}): Promise<ComprasCuotasListResponse> {
  return apiGet<ComprasCuotasListResponse>("/api/tarjetas-cuotas", { ...params });
}

export function fetchCompraDetalle(idPagoTarjeta: number): Promise<CompraCuotasDetalle> {
  return apiGet<CompraCuotasDetalle>(`/api/tarjetas-cuotas/${idPagoTarjeta}`);
}
