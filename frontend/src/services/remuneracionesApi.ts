/**
 * Typed client for the /api/remuneraciones contract (see
 * specs/005-egresos-y-ventas-menores/contracts/egresos-y-ventas-menores-api.md).
 * GET-only — this module never creates, edits, or deletes datos (FR-008).
 *
 * `PagoRemuneracion` is an independent listing, never nested under a
 * `Remuneracion`: `Pagos Remuneraciones.IdEmpleado` is not a foreign key
 * into `Contactos` (confirmed against real data — see research.md).
 */

import { apiGet } from "@/services/apiClient";

export interface Remuneracion {
  idSalario: number;
  idContacto: number | null;
  empleado: string | null;
  fechaPago: string | null;
  periodoLiquidado: string | null;
  importe: number | null;
}

export interface RemuneracionesListResponse {
  items: Remuneracion[];
  page: number;
  pageSize: number;
  total: number;
}

export interface PagoRemuneracion {
  idPago: number;
  fecha: string | null;
  cuenta: string | null;
  caja: string | null;
  importe: number | null;
}

export interface PagosRemuneracionListResponse {
  items: PagoRemuneracion[];
  page: number;
  pageSize: number;
  total: number;
}

export function fetchRemuneraciones(params: {
  empleado?: string;
  periodoLiquidado?: string;
  page?: number;
  pageSize?: number;
}): Promise<RemuneracionesListResponse> {
  return apiGet<RemuneracionesListResponse>("/api/remuneraciones", { ...params });
}

export function fetchPagosRemuneracion(params: {
  page?: number;
  pageSize?: number;
}): Promise<PagosRemuneracionListResponse> {
  return apiGet<PagosRemuneracionListResponse>("/api/remuneraciones/pagos", { ...params });
}
