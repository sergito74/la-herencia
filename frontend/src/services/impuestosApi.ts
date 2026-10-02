/**
 * Typed client for the /api/impuestos contract (see
 * specs/005-egresos-y-ventas-menores/contracts/egresos-y-ventas-menores-api.md).
 * Boletas: alta/edición/baja desde 033-alta-impuestos (reemplaza FR-008 de 005); retenciones solo lectura.
 */

import { apiDelete, apiGet, apiPost, apiPut } from "@/services/apiClient";

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

// --- 033-alta-impuestos: alta, edición y baja de boletas ---

export interface TipoImpuestoOpcion {
  idTipoImpuesto: number;
  nombre: string;
}

export interface OrganismoOpcion {
  idContacto: number;
  nombre: string;
  tipos: TipoImpuestoOpcion[];
}

export interface ImpuestoInput {
  idOrganismo: number;
  idTipoImpuesto: number;
  fecha: string;
  periodoLiquidado: string | null;
  numeroDocumento: string | null;
  importe: number;
  documentoOriginal: string | null;
}

export interface ImpuestoDetalle extends Partial<ImpuestoInput> {
  idImpuesto: number;
  organismo: string | null;
  tipoImpuesto: string | null;
}

export function fetchCatalogoImpuestos(): Promise<{ organismos: OrganismoOpcion[] }> {
  return apiGet<{ organismos: OrganismoOpcion[] }>("/api/impuestos/catalogo");
}

export function fetchImpuesto(idImpuesto: number): Promise<ImpuestoDetalle> {
  return apiGet<ImpuestoDetalle>(`/api/impuestos/${idImpuesto}`);
}

export function crearImpuesto(body: ImpuestoInput): Promise<ImpuestoDetalle> {
  return apiPost<ImpuestoDetalle>("/api/impuestos", body);
}

export function editarImpuesto(idImpuesto: number, body: ImpuestoInput): Promise<ImpuestoDetalle> {
  return apiPut<ImpuestoDetalle>(`/api/impuestos/${idImpuesto}`, body);
}

export function eliminarImpuesto(idImpuesto: number): Promise<void> {
  return apiDelete(`/api/impuestos/${idImpuesto}`);
}
