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
  /** 041: cargas vigentes a socios de esta boleta. */
  aCargoDe?: { idSocio: number; socio: string; importe: string }[];
  estadoDevolucion?: EstadoDevolucion | null;
  pendienteNominal?: string | null;
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
  particular?: boolean;
}): Promise<ImpuestosListResponse> {
  const { particular, ...resto } = params;
  return apiGet<ImpuestosListResponse>("/api/impuestos", { ...resto, particular: particular ? "true" : undefined });
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


// --- 041 impuestos particulares (specs/041-impuestos-particulares/contracts/api.md) ---

export type EstadoDevolucion = "devuelto" | "parcial" | "pendiente";

export interface DevolucionVinculo {
  idVinculo: number;
  idMovimientoSocio: number;
  importe: string;
  estado: "vigente" | "anulada";
}

export interface CargaParticular {
  idCarga: number;
  idImpuesto: number;
  idSocio: number;
  socio: string;
  importe: string;
  motivo: string;
  partida: string | null;
  titularOscar: boolean;
  estado: "vigente" | "anulada";
  idMovimientoSocio: number;
  devuelto: string;
  pendienteNominal: string;
  estadoDevolucion: EstadoDevolucion | null;
  devoluciones: DevolucionVinculo[];
  motivoAnulacion: string | null;
}

export interface PartidaInfo {
  partida: string | null;
  estado: "vigente" | "ambigua" | "sin_cargas" | "desconocida";
  idSocio: number | null;
  socio: string | null;
  candidatos: { idSocio: number; socio: string }[];
  titularOscar: boolean;
}

export interface ParticularImpuesto {
  idImpuesto: number;
  importe: string;
  aCargoDeSocios: string;
  parteEmpresa: string;
  cargas: CargaParticular[];
  avisos: ({ tipo: "partida" } & PartidaInfo)[];
}

export interface CargaInput {
  claveIdempotencia: string;
  idSocio: number;
  importe?: string;
  porcentaje?: string;
  motivo: string;
  partida?: string | null;
  titularOscar?: boolean;
  reemplazarMovimientoManual?: number;
  confirmarCuentaCerrada?: boolean;
  ignorarManuales?: boolean;
}

export type DevolucionInput =
  | { claveIdempotencia: string; idMovimientoSocio: number; importe: string }
  | { claveIdempotencia: string; fecha: string; importe: string; medio?: string; motivo: string };

export const fetchParticular = (idImpuesto: number, partida?: string) =>
  apiGet<ParticularImpuesto>(`/api/impuestos/${idImpuesto}/particular`, { partida });
export const crearCargaParticular = (idImpuesto: number, body: CargaInput) =>
  apiPost<CargaParticular>(`/api/impuestos/${idImpuesto}/particular`, body);
export const registrarDevolucion = (idCarga: number, body: DevolucionInput) =>
  apiPost<CargaParticular & { idVinculo: number }>(`/api/impuestos/particular/${idCarga}/devoluciones`, body);
export const anularDevolucion = (idCarga: number, idVinculo: number, motivo: string) =>
  apiPost<CargaParticular>(`/api/impuestos/particular/${idCarga}/devoluciones/${idVinculo}/anular`, { motivo });
export const anularCargaParticular = (idCarga: number, motivo: string) =>
  apiPost<CargaParticular>(`/api/impuestos/particular/${idCarga}/anular`, { motivo });
export const consultarPartida = (partida: string) =>
  apiGet<PartidaInfo>(`/api/impuestos/partidas/${partida.split("/").map(encodeURIComponent).join("/")}`);
