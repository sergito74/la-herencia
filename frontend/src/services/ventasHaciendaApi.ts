/**
 * Typed client for the /api/ventas-hacienda contract (see
 * specs/005-egresos-y-ventas-menores/contracts/egresos-y-ventas-menores-api.md).
 * GET-only — this module never creates, edits, or deletes datos (FR-008).
 *
 * `Retencion` is an independent listing, never nested under a
 * `VentaHacienda`: there is no reliable key linking a retención to a
 * specific venta (confirmed against real data — see research.md).
 */

import { apiGet } from "@/services/apiClient";

export interface LineaVentaHacienda {
  idDetalleVenta: number;
  comprador: string | null;
  tipoHacienda: string | null;
  cantidad: number | null;
  unidadMedida: string | null;
  pesoTotal: number | null;
  precioUnitarioA: number | null;
  precioUnitarioB: number | null;
  /** = cantidad * (precioUnitarioA + precioUnitarioB), fórmula confirmada
   * contra el formulario Access real (Subformulario Detalle Venta Feria
   * Hacienda, control TxtTotal). */
  importe: number | null;
}

export interface VentaHacienda {
  idVenta: number;
  fecha: string | null;
  consignatario: string | null;
  numeroDocumento: string | null;
  lineas: LineaVentaHacienda[];
}

export interface VentasHaciendaListResponse {
  items: VentaHacienda[];
  page: number;
  pageSize: number;
  total: number;
}

export interface RetencionVentaHacienda {
  idRetencion: number;
  fecha: string | null;
  contacto: string | null;
  documento: string | null;
  numeroDocumento: string | null;
  importe: number | null;
}

export interface RetencionesVentaHaciendaListResponse {
  items: RetencionVentaHacienda[];
  page: number;
  pageSize: number;
  total: number;
}

export function fetchVentasHacienda(params: {
  consignatario?: string;
  fechaDesde?: string;
  fechaHasta?: string;
  page?: number;
  pageSize?: number;
}): Promise<VentasHaciendaListResponse> {
  return apiGet<VentasHaciendaListResponse>("/api/ventas-hacienda", { ...params });
}

export function fetchRetencionesVentaHacienda(params: {
  contacto?: string;
  fechaDesde?: string;
  fechaHasta?: string;
  page?: number;
  pageSize?: number;
}): Promise<RetencionesVentaHaciendaListResponse> {
  return apiGet<RetencionesVentaHaciendaListResponse>("/api/ventas-hacienda/retenciones", {
    ...params,
  });
}
