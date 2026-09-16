/**
 * Typed client for the /api/compras contract (see
 * specs/002-compras/contracts/compras-api.md). GET-only — this module never
 * creates, edits, or deletes compras (FR-010).
 */

import { apiGet } from "@/services/apiClient";

export interface Proveedor {
  idContacto: number;
  razonSocial: string | null;
}

export interface Compra {
  idCompra: number;
  fecha: string | null;
  proveedor: Proveedor | null;
  tipoDocumento: string | null;
  numeroDocumento: string | null;
}

export interface ComprasListResponse {
  items: Compra[];
  page: number;
  pageSize: number;
  total: number;
}

export interface Imputacion {
  idRubro: number | null;
  rubro: string | null;
  idCentroCosto: number | null;
  centroCosto: string | null;
  idDestino: number | null;
  destino: string | null;
  idCampania: number | null;
  campania: string | null;
}

export interface LineaCompra {
  idDetalleCompra: number;
  productoServicio: string | null;
  cantidad: number | null;
  precioUnitario: number | null;
  iva: number | null;
  // null indica explícitamente "sin imputar" (FR-006), nunca se omite.
  imputacion: Imputacion | null;
}

export interface CompraDetalle {
  idCompra: number;
  fecha: string | null;
  proveedor: Proveedor | null;
  tipoDocumento: string | null;
  numeroDocumento: string | null;
  conceptosNoGravados: number | null;
  ingresosBrutos: number | null;
  lineas: LineaCompra[];
}

export interface ComprasSearchParams {
  proveedor?: string;
  numeroDocumento?: string;
  fechaDesde?: string;
  fechaHasta?: string;
  page?: number;
  pageSize?: number;
}

export function fetchCompras(
  params: ComprasSearchParams
): Promise<ComprasListResponse> {
  return apiGet<ComprasListResponse>("/api/compras", { ...params });
}

export function fetchCompraDetalle(idCompra: number): Promise<CompraDetalle> {
  return apiGet<CompraDetalle>(`/api/compras/${idCompra}`);
}

export interface MovimientoTrazabilidad {
  origenTipo: string | null;
  idOrigen: number;
  documento: string | null;
  fecha: string | null;
  importe: number | null;
  tipoImporte: string | null;
}

export interface TrazabilidadCompra {
  idCompra: number;
  movimientos: MovimientoTrazabilidad[];
}

export function fetchCompraTrazabilidad(
  idCompra: number
): Promise<TrazabilidadCompra> {
  return apiGet<TrazabilidadCompra>(`/api/compras/${idCompra}/trazabilidad`);
}
