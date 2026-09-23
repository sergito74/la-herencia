/**
 * Typed client for the /api/cuentas-corrientes contract (see
 * specs/004-cuentas-corrientes/contracts/cuentas-corrientes-api.md).
 * GET-only — this module never creates, edits, or deletes datos (FR-010).
 */

import { API_BASE_URL, apiGet } from "@/services/apiClient";

export interface Contacto {
  idContacto: number;
  razonSocial: string | null;
  tipoContacto: string | null;
}

export interface ContactosListResponse {
  items: Contacto[];
}

export interface Saldo {
  idContacto: number;
  saldoParcial: number | null;
}

export interface Origen {
  tipo:
    | "compra"
    | "tesoreria"
    | "impuesto"
    | "retencion"
    | "remuneracion"
    | "arrendamiento"
    | "venta_hacienda"
    | "fuera_de_alcance"
    | "no_disponible";
  idCompra?: number | null;
  proveedor?: string | null;
  numeroDocumento?: string | null;
  medio?: "bna" | "galicia" | "efectivo" | "valores_recibidos" | null;
  idMovimiento?: number | null;
  fecha?: string | null;
  importe?: number | null;
  origenTipo?: string | null;
  motivo?: string | null;
  // specs/005-egresos-y-ventas-menores
  idImpuesto?: number | null;
  tipoImpuesto?: string | null;
  idRetencion?: number | null;
  numeroCertificado?: string | null;
  idSalario?: number | null;
  periodoLiquidado?: string | null;
  empleado?: string | null;
  idAlquiler?: number | null;
  contacto?: string | null;
  importeTotalContrato?: number | null;
}

export interface MovimientoCuentaCorriente {
  fecha: string | null;
  documento: string | null;
  numeroDocumento: string | null;
  deuda: number | null;
  credito: number | null;
  /** Saldo acumulado hasta este movimiento — replica la columna que
   * muestra el formulario Access real (SbfrmMovCuenta). */
  saldoParcial: number | null;
  origen: Origen;
}

export interface MovimientosListResponse {
  items: MovimientoCuentaCorriente[];
  page: number;
  pageSize: number;
  total: number;
}

export function fetchContactos(params: {
  q?: string;
  tipoContacto?: string;
}): Promise<ContactosListResponse> {
  return apiGet<ContactosListResponse>("/api/cuentas-corrientes/contactos", {
    ...params,
  });
}

export function fetchSaldo(idContacto: number): Promise<Saldo> {
  return apiGet<Saldo>(`/api/cuentas-corrientes/contactos/${idContacto}/saldo`);
}

export function fetchMovimientos(
  idContacto: number,
  params: { fechaDesde?: string; fechaHasta?: string; page?: number; pageSize?: number }
): Promise<MovimientosListResponse> {
  return apiGet<MovimientosListResponse>(
    `/api/cuentas-corrientes/contactos/${idContacto}/movimientos`,
    { ...params }
  );
}

export function urlExportarCuenta(
  idContacto: number,
  params: { fechaDesde?: string; fechaHasta?: string } = {}
): string {
  const url = new URL(`/api/cuentas-corrientes/contactos/${idContacto}/exportar`, API_BASE_URL);
  if (params.fechaDesde) url.searchParams.set("fechaDesde", params.fechaDesde);
  if (params.fechaHasta) url.searchParams.set("fechaHasta", params.fechaHasta);
  return url.toString();
}

export interface SaldoContacto {
  idContacto: number;
  razonSocial: string | null;
  saldoParcial: number | null;
}

export interface SaldosResponse {
  items: SaldoContacto[];
}

export type OrdenSaldos = "razonSocial" | "saldo";

export function fetchSaldos(orden: OrdenSaldos = "razonSocial"): Promise<SaldosResponse> {
  return apiGet<SaldosResponse>("/api/cuentas-corrientes/saldos", { orden });
}

export function urlExportarSaldos(orden: OrdenSaldos = "razonSocial"): string {
  const url = new URL("/api/cuentas-corrientes/saldos/exportar", API_BASE_URL);
  url.searchParams.set("orden", orden);
  return url.toString();
}
