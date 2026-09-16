/**
 * Typed client for the /api/impuestos contract (see
 * specs/005-egresos-y-ventas-menores/contracts/egresos-y-ventas-menores-api.md).
 * GET-only — this module never creates, edits, or deletes datos (FR-008).
 */

import { apiGet } from "@/services/apiClient";

export interface Impuesto {
  idImpuesto: number;
  fecha: string | null;
  tipoImpuesto: string | null;
  periodoLiquidado: string | null;
  numeroDocumento: string | null;
  importe: number | null;
  idOrganismo: number | null;
  organismo: string | null;
}

export interface ImpuestosListResponse {
  items: Impuesto[];
  page: number;
  pageSize: number;
  total: number;
}

export interface Retencion {
  idRetencion: number;
  numeroCertificado: string | null;
  fecha: string | null;
  idContacto: number | null;
  contacto: string | null;
  importe: number | null;
}

export interface RetencionesListResponse {
  items: Retencion[];
  page: number;
  pageSize: number;
  total: number;
}

export function fetchImpuestos(params: {
  organismo?: string;
  fechaDesde?: string;
  fechaHasta?: string;
  page?: number;
  pageSize?: number;
}): Promise<ImpuestosListResponse> {
  return apiGet<ImpuestosListResponse>("/api/impuestos", { ...params });
}

export function fetchRetenciones(params: {
  contacto?: string;
  fechaDesde?: string;
  fechaHasta?: string;
  page?: number;
  pageSize?: number;
}): Promise<RetencionesListResponse> {
  return apiGet<RetencionesListResponse>("/api/impuestos/retenciones", { ...params });
}
