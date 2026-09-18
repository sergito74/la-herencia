/**
 * Resúmenes de tarjeta (Historia 1) — ver
 * specs/008-tarjetas/contracts/tarjetas-api.md. Escribe exclusivamente
 * contra `WC`.
 */

import { apiDelete, apiGet, apiPost, apiPut } from "@/services/apiClient";

export interface LineaConsumoInput {
  fechaCompra: string;
  detalle: string;
  importe: number;
  fechaVencimientoCompra?: string | null;
  idContacto?: number | null;
  nroDocumento?: string | null;
}

export interface LineaConsumo extends LineaConsumoInput {
  idLineaConsumo: number | null;
}

export interface ResumenAltaInput {
  idTarjeta: number;
  codigo: string;
  fechaCierre: string;
  fechaVencimiento: string;
  impuestoSellos?: number;
  gastosAdmin?: number;
  mantCuenta?: number;
  renovAnual?: number;
  promocionBNA?: number;
  creditoContingente?: number;
  intFinanc?: number;
  intCompens?: number;
  iva105?: number;
  percepIVA105?: number;
  iva21?: number;
  percepIVA21?: number;
  percepIIBB?: number;
  ajusteResAnterior?: number;
  lineas: LineaConsumoInput[];
}

export interface ResumenDetalle extends ResumenAltaInput {
  idResumen: number;
  tarjeta: string | null;
  totalCalculado: number;
  lineas: LineaConsumo[];
  warnings: string[];
}

export interface ResumenListItem {
  idResumen: number;
  idTarjeta: number;
  tarjeta: string | null;
  codigo: string;
  fechaCierre: string | null;
  fechaVencimiento: string | null;
  totalCalculado: number;
  soloCabecera: boolean;
}

export interface ResumenesListResponse {
  items: ResumenListItem[];
  page: number;
  pageSize: number;
  total: number;
}

export function fetchResumenes(params: {
  idTarjeta?: number;
  fechaCierreDesde?: string;
  fechaCierreHasta?: string;
  fechaVencimientoDesde?: string;
  fechaVencimientoHasta?: string;
  page?: number;
  pageSize?: number;
}): Promise<ResumenesListResponse> {
  return apiGet<ResumenesListResponse>("/api/tarjetas-resumenes", { ...params });
}

export function fetchResumenDetalle(idResumen: number): Promise<ResumenDetalle> {
  return apiGet<ResumenDetalle>(`/api/tarjetas-resumenes/${idResumen}`);
}

export function crearResumen(input: ResumenAltaInput): Promise<ResumenDetalle> {
  return apiPost<ResumenDetalle>("/api/tarjetas-resumenes", input);
}

export function actualizarResumen(idResumen: number, input: ResumenAltaInput, lockToken: string): Promise<ResumenDetalle> {
  return apiPut<ResumenDetalle>(`/api/tarjetas-resumenes/${idResumen}`, input, { "X-Lock-Token": lockToken });
}

export function eliminarResumen(idResumen: number, lockToken: string): Promise<void> {
  return apiDelete(`/api/tarjetas-resumenes/${idResumen}`, { "X-Lock-Token": lockToken });
}

export interface LockResumenResponse {
  idResumen: number;
  lockToken: string;
  expiresAt: string;
}

export function adquirirLockResumen(idResumen: number, lockToken: string, force = false): Promise<LockResumenResponse> {
  return apiPost<LockResumenResponse>(`/api/tarjetas-resumenes/${idResumen}/lock`, { lockToken, force });
}

export function liberarLockResumen(idResumen: number, lockToken: string, keepalive = false): Promise<void> {
  return apiDelete(`/api/tarjetas-resumenes/${idResumen}/lock`, { "X-Lock-Token": lockToken }, keepalive);
}
