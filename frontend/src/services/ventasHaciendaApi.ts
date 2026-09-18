/**
 * Typed client for the /api/ventas-hacienda contract (see
 * specs/005-egresos-y-ventas-menores/contracts/egresos-y-ventas-menores-api.md).
 * GET-only — this module never creates, edits, or deletes datos (FR-008).
 *
 * `Retencion` is an independent listing, never nested under a
 * `VentaHacienda`: there is no reliable key linking a retención to a
 * specific venta (confirmed against real data — see research.md).
 */

import { apiDelete, apiGet, apiPost, apiPut } from "@/services/apiClient";
import type { TipoContacto } from "@/services/contactosApi";

/** research.md §2: histórico real usa Comprador/Consignatario/Multiple, no solo "Consignatario". */
export const TIPOS_CONTACTO_VENTA_HACIENDA: TipoContacto[] = ["Comprador", "Consignatario", "Multiple"];

export interface LineaVentaHacienda {
  idDetalleVenta: number;
  idComprador: number | null;
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
  idConsignatario: number | null;
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
  idContacto: number | null;
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

// --- Alta/edición/eliminación (007-ventas-hacienda-granos) — escriben
// exclusivamente contra `WC` (ver apiClient.ts). ---

export interface LineaVentaHaciendaInput {
  idComprador: number;
  idTipoProducto: number;
  cantidad: number;
  unidadMedida?: string | null;
  pesoTotal?: number | null;
  precioUnitarioA: number;
  precioUnitarioB?: number;
}

export interface VencimientoVentaInput {
  fecha: string;
  importe: number;
}

export interface VentaHaciendaAltaInput {
  idConsignatario: number;
  idEstablecimiento: number;
  idTipoDocumento: number;
  numeroDocumento: string;
  fecha: string;
  porcComision?: number;
  visMunicipal?: number;
  balanza?: number;
  gsVsNoGravados?: number;
  alicuotaIVA?: number;
  retencionGanancias?: number;
  retencionIVA?: number;
  ingresosBrutos?: number;
  leyDeSellos?: number;
  flete?: number;
  gastosVarios?: number;
  complemento?: number;
  documentoOriginal?: string | null;
  lineas: LineaVentaHaciendaInput[];
  vencimientos: VencimientoVentaInput[];
}

export interface LineaVentaHaciendaCalculada extends LineaVentaHaciendaInput {
  comprador: string | null;
  idDetalleVenta: number | null;
  importe: number;
}

export interface VencimientoVentaCalculado extends VencimientoVentaInput {
  idVencimientoVenta: number | null;
}

export interface VentaHaciendaDetalle extends VentaHaciendaAltaInput {
  idVenta: number;
  consignatario: string | null;
  subTotal: number;
  subtotalB: number;
  comision: number;
  iva: number;
  importe: number;
  importeTotal: number;
  lineas: LineaVentaHaciendaCalculada[];
  vencimientos: VencimientoVentaCalculado[];
  warnings: string[];
}

export interface EstablecimientoItem {
  idEstablecimiento: number;
  establecimiento: string | null;
}

export interface TipoDocumentoItem {
  idTipoDocumento: number;
  tipoDocumento: string | null;
}

export interface TipoHaciendaItem {
  idTipoHacienda: number;
  tipoHacienda: string | null;
}

export interface FiltrosVentaHaciendaResponse {
  establecimientos: EstablecimientoItem[];
  tiposDocumento: TipoDocumentoItem[];
  tiposHacienda: TipoHaciendaItem[];
}

export function fetchFiltrosVentaHacienda(): Promise<FiltrosVentaHaciendaResponse> {
  return apiGet<FiltrosVentaHaciendaResponse>("/api/ventas-hacienda/filtros");
}

/** Alta de una venta de hacienda completa. Escribe solo en `WC`. */
export function crearVentaHacienda(input: VentaHaciendaAltaInput): Promise<VentaHaciendaDetalle> {
  return apiPost<VentaHaciendaDetalle>("/api/ventas-hacienda", input);
}

export function fetchVentaHaciendaDetalle(idVenta: number): Promise<VentaHaciendaDetalle> {
  return apiGet<VentaHaciendaDetalle>(`/api/ventas-hacienda/${idVenta}`);
}

/** Edición: reemplaza cabecera+líneas+vencimientos por completo. Requiere el lock adquirido. */
export function actualizarVentaHacienda(
  idVenta: number,
  input: VentaHaciendaAltaInput,
  lockToken: string
): Promise<VentaHaciendaDetalle> {
  return apiPut<VentaHaciendaDetalle>(`/api/ventas-hacienda/${idVenta}`, input, {
    "X-Lock-Token": lockToken,
  });
}

/** Eliminación definitiva (venta cargada por error). Requiere el lock adquirido. */
export function eliminarVentaHacienda(idVenta: number, lockToken: string): Promise<void> {
  return apiDelete(`/api/ventas-hacienda/${idVenta}`, { "X-Lock-Token": lockToken });
}

export interface LockVentaHaciendaResponse {
  idVenta: number;
  lockToken: string;
  expiresAt: string;
}

/** Adquiere o renueva el bloqueo exclusivo de edición. 409 si otra sesión lo tiene. */
export function adquirirLockVentaHacienda(
  idVenta: number,
  lockToken: string,
  force = false
): Promise<LockVentaHaciendaResponse> {
  return apiPost<LockVentaHaciendaResponse>(`/api/ventas-hacienda/${idVenta}/lock`, {
    lockToken,
    force,
  });
}

/** Libera el bloqueo. `keepalive` para liberarlo de forma confiable al cerrar la pestaña. */
export function liberarLockVentaHacienda(
  idVenta: number,
  lockToken: string,
  keepalive = false
): Promise<void> {
  return apiDelete(`/api/ventas-hacienda/${idVenta}/lock`, { "X-Lock-Token": lockToken }, keepalive);
}

// --- Documentos relacionados (vínculo manual entre ventas del mismo consignatario) ---

export interface DocumentoRelacionadoVentaHacienda {
  idVenta: number;
  fecha: string | null;
  tipoDocumento: string | null;
  numeroDocumento: string | null;
}

export function fetchDocumentosRelacionadosVentaHacienda(
  idVenta: number
): Promise<DocumentoRelacionadoVentaHacienda[]> {
  return apiGet<DocumentoRelacionadoVentaHacienda[]>(`/api/ventas-hacienda/${idVenta}/relacionados`);
}

export function agregarDocumentoRelacionadoVentaHacienda(
  idVenta: number,
  idVentaRelacionada: number
): Promise<void> {
  return apiPost(`/api/ventas-hacienda/${idVenta}/relacionados`, { idVentaRelacionada });
}

export function quitarDocumentoRelacionadoVentaHacienda(
  idVenta: number,
  idVentaRelacionada: number
): Promise<void> {
  return apiDelete(`/api/ventas-hacienda/${idVenta}/relacionados/${idVentaRelacionada}`);
}
