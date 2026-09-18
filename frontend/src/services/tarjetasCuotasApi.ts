/**
 * Compras en cuotas (Historia 3) — ver
 * specs/008-tarjetas/contracts/tarjetas-api.md. No vinculadas a una
 * tarjeta del catálogo (data-model.md). Escribe exclusivamente contra `WC`.
 */

import { apiDelete, apiGet, apiPatch, apiPost, apiPut } from "@/services/apiClient";

export interface CompraCuotasAltaInput {
  idContacto: number;
  fecha: string;
  nroComprobante: number;
  importeTotal: number;
  cantidadCuotas: number;
}

export interface Cuota {
  idCuota: number;
  numeroCuota: number;
  fechaVencimiento: string;
  importe: number;
  cobrado: boolean;
}

export interface CompraCuotasDetalle extends CompraCuotasAltaInput {
  idPagoTarjeta: number;
  contacto: string | null;
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

export function crearCompra(input: CompraCuotasAltaInput): Promise<CompraCuotasDetalle> {
  return apiPost<CompraCuotasDetalle>("/api/tarjetas-cuotas", input);
}

export function actualizarCompra(
  idPagoTarjeta: number,
  input: CompraCuotasAltaInput,
  lockToken: string
): Promise<CompraCuotasDetalle> {
  return apiPut<CompraCuotasDetalle>(`/api/tarjetas-cuotas/${idPagoTarjeta}`, input, { "X-Lock-Token": lockToken });
}

export function eliminarCompra(idPagoTarjeta: number, lockToken: string): Promise<void> {
  return apiDelete(`/api/tarjetas-cuotas/${idPagoTarjeta}`, { "X-Lock-Token": lockToken });
}

export function marcarCobrada(idPagoTarjeta: number, idCuota: number, cobrado: boolean): Promise<Cuota> {
  return apiPatch<Cuota>(`/api/tarjetas-cuotas/${idPagoTarjeta}/cuotas/${idCuota}`, { cobrado });
}

export interface LockCompraResponse {
  idPagoTarjeta: number;
  lockToken: string;
  expiresAt: string;
}

export function adquirirLockCompra(idPagoTarjeta: number, lockToken: string, force = false): Promise<LockCompraResponse> {
  return apiPost<LockCompraResponse>(`/api/tarjetas-cuotas/${idPagoTarjeta}/lock`, { lockToken, force });
}

export function liberarLockCompra(idPagoTarjeta: number, lockToken: string, keepalive = false): Promise<void> {
  return apiDelete(`/api/tarjetas-cuotas/${idPagoTarjeta}/lock`, { "X-Lock-Token": lockToken }, keepalive);
}
