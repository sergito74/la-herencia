/**
 * Typed client for the /api/ventas-granos contract (007-ventas-hacienda-granos)
 * — dominio 100% nuevo, lectura + alta/edición/eliminación desde el
 * arranque. Escribe exclusivamente contra `WC` (ver apiClient.ts).
 */

import { apiDelete, apiGet, apiPost, apiPut } from "@/services/apiClient";
import type { TipoContacto } from "@/services/contactosApi";

/** research.md §3: histórico real 100% tipo Multiple, admitir también Comprador/Consignatario. */
export const TIPOS_CONTACTO_VENTA_GRANOS: TipoContacto[] = ["Comprador", "Consignatario", "Multiple"];

export interface ConsignatarioGranos {
  idContacto: number;
  razonSocial: string | null;
}

export interface VentaGranos {
  idVenta: number;
  fecha: string | null;
  consignatario: ConsignatarioGranos | null;
  tipoDocumento: string | null;
  numeroDocumento: string | null;
  grano: string | null;
  campania: string | null;
}

export interface VentaGranosListResponse {
  items: VentaGranos[];
  page: number;
  pageSize: number;
  total: number;
}

export interface AjusteGranos {
  idAjuste: number;
  concepto: string | null;
  importe: number | null;
  alicuotaIVA: number | null;
}

export interface DeduccionGranos {
  idDeduccion: number;
  idConcepto: number | null;
  concepto: string | null;
  detalle: string | null;
  porc: number | null;
  baseCalculo: number | null;
  alicuota: number | null;
}

export interface VentaGranosDetalle {
  idVenta: number;
  idConsignatario: number;
  idTipoDocumento: number;
  numeroDocumento: string;
  fecha: string;
  precioUnitario: number;
  tipoCambio: number | null;
  gradoOperacion: string | null;
  idProducto: number;
  tipoDeGrano: string | null;
  campania: string | null;
  flete: number;
  nroDeposito: string | null;
  gradoMercaderia: string | null;
  factor: number;
  contProteico: number | null;
  cantidadEntregada: number;
  cantidadVendida: number;
  alicuotaIVA: number;
  retencionIVA: number;
  retIG: number;
  percepciones: number;
  otraRetenciones: number;
  sellado: number;
  derechoRegistro: number;
  honorariosCamara: number;
  aCuentaCalidad: number;
  iibb: number;
  documentoOriginal: string | null;
  ajustes: AjusteGranos[];
  deducciones: DeduccionGranos[];
  precioKg: number;
  subTotal: number;
  iva: number;
  importeConIVA: number;
  totalOperacion: number;
  totalRetenciones: number;
  totalDeducciones: number;
  importeNetoAPercibir: number;
  warnings: string[];
}

export function fetchVentasGranos(params: {
  consignatario?: string;
  numeroDocumento?: string;
  fechaDesde?: string;
  fechaHasta?: string;
  campania?: string;
  sortBy?: string;
  sortDir?: "asc" | "desc";
  page?: number;
  pageSize?: number;
}): Promise<VentaGranosListResponse> {
  return apiGet<VentaGranosListResponse>("/api/ventas-granos", { ...params });
}

export function fetchVentaGranosDetalle(idVenta: number): Promise<VentaGranosDetalle> {
  return apiGet<VentaGranosDetalle>(`/api/ventas-granos/${idVenta}`);
}

export interface GranoItem {
  idGrano: number;
  grano: string | null;
}

export interface TipoDocumentoItemGranos {
  idTipoDocumento: number;
  tipoDocumento: string | null;
}

export interface ConceptoDeduccionItem {
  idConcepto: number;
  concepto: string | null;
}

export interface FiltrosVentaGranosResponse {
  granos: GranoItem[];
  tiposDocumento: TipoDocumentoItemGranos[];
  conceptosDeducciones: ConceptoDeduccionItem[];
}

export function fetchFiltrosVentasGranos(): Promise<FiltrosVentaGranosResponse> {
  return apiGet<FiltrosVentaGranosResponse>("/api/ventas-granos/filtros");
}

// --- Alta/edición/eliminación ---

export interface AjusteInput {
  concepto: string;
  importe: number;
  alicuotaIVA?: number;
}

export interface DeduccionInput {
  idConcepto: number;
  detalle?: string | null;
  porc: number;
  baseCalculo: number;
  alicuota?: number;
}

export interface VentaGranosAltaInput {
  idConsignatario: number;
  idTipoDocumento: number;
  idProducto: number;
  numeroDocumento: string;
  fecha: string;
  precioUnitario: number;
  tipoCambio?: number | null;
  gradoOperacion?: string | null;
  tipoDeGrano?: string | null;
  campania?: string | null;
  flete?: number;
  nroDeposito?: string | null;
  gradoMercaderia?: string | null;
  factor?: number;
  contProteico?: number | null;
  cantidadEntregada: number;
  cantidadVendida: number;
  alicuotaIVA?: number;
  retencionIVA?: number;
  retIG?: number;
  percepciones?: number;
  otraRetenciones?: number;
  sellado?: number;
  derechoRegistro?: number;
  honorariosCamara?: number;
  aCuentaCalidad?: number;
  iibb?: number;
  documentoOriginal?: string | null;
  ajustes: AjusteInput[];
  deducciones: DeduccionInput[];
}

/** Alta de una venta de granos completa. Escribe solo en `WC`. */
export function crearVentaGranos(input: VentaGranosAltaInput): Promise<VentaGranosDetalle> {
  return apiPost<VentaGranosDetalle>("/api/ventas-granos", input);
}

/** Edición: reemplaza cabecera+ajustes+deducciones por completo. Requiere el lock adquirido. */
export function actualizarVentaGranos(
  idVenta: number,
  input: VentaGranosAltaInput,
  lockToken: string
): Promise<VentaGranosDetalle> {
  return apiPut<VentaGranosDetalle>(`/api/ventas-granos/${idVenta}`, input, {
    "X-Lock-Token": lockToken,
  });
}

/** Eliminación definitiva (venta cargada por error). Requiere el lock adquirido. */
export function eliminarVentaGranos(idVenta: number, lockToken: string): Promise<void> {
  return apiDelete(`/api/ventas-granos/${idVenta}`, { "X-Lock-Token": lockToken });
}

export interface LockVentaGranosResponse {
  idVenta: number;
  lockToken: string;
  expiresAt: string;
}

/** Adquiere o renueva el bloqueo exclusivo de edición. 409 si otra sesión lo tiene. */
export function adquirirLockVentaGranos(
  idVenta: number,
  lockToken: string,
  force = false
): Promise<LockVentaGranosResponse> {
  return apiPost<LockVentaGranosResponse>(`/api/ventas-granos/${idVenta}/lock`, { lockToken, force });
}

/** Libera el bloqueo. `keepalive` para liberarlo de forma confiable al cerrar la pestaña. */
export function liberarLockVentaGranos(
  idVenta: number,
  lockToken: string,
  keepalive = false
): Promise<void> {
  return apiDelete(`/api/ventas-granos/${idVenta}/lock`, { "X-Lock-Token": lockToken }, keepalive);
}
