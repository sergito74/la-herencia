/**
 * Typed client for the /api/remuneraciones contract — lectura (ver
 * specs/005-egresos-y-ventas-menores) + alta (028, ver
 * specs/028-alta-liquidacion-remuneraciones/contracts/api.md).
 *
 * `PagoRemuneracion` is an independent listing, never nested under a
 * `Remuneracion`: `Pagos Remuneraciones.IdEmpleado` is not a foreign key
 * into `Contactos` (confirmed against real data — see research.md).
 */

import { API_BASE_URL, apiGet, apiPost, apiPut, ApiError } from "@/services/apiClient";

export interface Remuneracion {
  idSalario: number;
  idContacto: number | null;
  empleado: string | null;
  fechaPago: string | null;
  periodoLiquidado: string | null;
  importe: number | null;
  /** Valor crudo de `dbo.Remuneraciones.Recibo` — ver `documentoLocal.ts`
   * (`BASE_DOCUMENTOS_RECIBOS`, `esReciboAusente`) para cómo se resuelve. */
  recibo: string | null;
  /** 18/11/2026: pagos vinculados (socio, banco de Giamigli o caja) y su total. */
  pagado?: number;
  pagos?: { idPago: number; medio: "socio" | "galicia" | "bna" | "caja"; fecha: string; importe: number; socio?: string | null }[];
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

/** URL del PDF del recibo de sueldo, servido desde el disco local de esta
 * PC (ver `GET /api/remuneraciones/{idSalario}/recibo` — mismo patrón que
 * `urlDocumentoLocal` de Compras, pero acá el backend resuelve el archivo
 * solo, sin recibir una ruta). */
export function urlRecibo(idSalario: number): string {
  return new URL(`/api/remuneraciones/${idSalario}/recibo`, API_BASE_URL).toString();
}

/** Todos los conceptos monetarios se cargan siempre en positivo, tal como
 * figuran en el recibo real — el backend resta internamente los de
 * descuento (028, contracts/api.md). */
export interface NuevaLiquidacionRequest {
  idContacto: number;
  fechaPago: string;
  periodoLiquidado: string;
  sueldoBasico?: number;
  antiguedad?: number;
  adicFuturosAumentos?: number;
  diaGremio?: number;
  aguinaldo?: number;
  vacaciones?: number;
  ajuste?: number;
  ajusteNoRemunerativo?: number;
  redondeo?: number;
  bonificacionAdicional?: number;
  jubilacion?: number;
  ley19032?: number;
  obraSocial?: number;
  obraSocialAcuerdos?: number;
  aporteSindical?: number;
  servicioDeSepelio?: number;
  confirmarDuplicado?: boolean;
}

export interface NuevaLiquidacionResponse {
  idSalario: number;
  importeNeto: number;
  recibo: string | null;
}

/** `POST /api/remuneraciones` — puede rechazar con 409 (ApiError.status)
 * si ya existe una liquidación para el mismo empleado+período; el
 * llamador decide si reintenta con `confirmarDuplicado: true` (FR-004,
 * no bloquea — ver `NuevaLiquidacionForm.tsx`). */
export function crearLiquidacion(request: NuevaLiquidacionRequest): Promise<NuevaLiquidacionResponse> {
  return apiPost<NuevaLiquidacionResponse>("/api/remuneraciones", request);
}

export interface AdjuntarReciboResponse {
  idSalario: number;
  recibo: string;
}

/** `POST /api/remuneraciones/{idSalario}/recibo` — multipart, PDF only
 * (máx. 10 MB, SC-004). */
export async function subirRecibo(idSalario: number, archivo: File): Promise<AdjuntarReciboResponse> {
  const url = new URL(`/api/remuneraciones/${idSalario}/recibo`, API_BASE_URL);
  const formData = new FormData();
  formData.append("archivo", archivo);
  const response = await fetch(url.toString(), {
    method: "POST",
    body: formData,
    credentials: "include",
  });
  if (!response.ok) {
    const texto = await response.text().catch(() => "");
    let detalle = texto;
    try {
      const parsed = JSON.parse(texto);
      if (typeof parsed?.detail === "string") detalle = parsed.detail;
    } catch {
      // texto crudo tal cual
    }
    throw new ApiError(response.status, detalle || response.statusText);
  }
  return (await response.json()) as AdjuntarReciboResponse;
}


export interface LiquidacionDetalle {
  idSalario: number;
  idContacto: number;
  empleado: string;
  fechaPago: string;
  periodoLiquidado: string;
  recibo: string | null;
  sueldoBasico: number;
  antiguedad: number;
  adicFuturosAumentos: number;
  diaGremio: number;
  aguinaldo: number;
  vacaciones: number;
  ajuste: number;
  ajusteNoRemunerativo: number;
  redondeo: number;
  bonificacionAdicional: number;
  jubilacion: number;
  ley19032: number;
  obraSocial: number;
  obraSocialAcuerdos: number;
  aporteSindical: number;
  servicioDeSepelio: number;
  importeTotal: number;
  netoRecibo: number;
}

export function fetchLiquidacion(idSalario: number): Promise<LiquidacionDetalle> {
  return apiGet<LiquidacionDetalle>(`/api/remuneraciones/${idSalario}`);
}

export function actualizarLiquidacion(
  idSalario: number,
  request: NuevaLiquidacionRequest
): Promise<NuevaLiquidacionResponse> {
  return apiPut<NuevaLiquidacionResponse>(`/api/remuneraciones/${idSalario}`, request);
}

export function registrarPagoAdicionalCaja(
  idSalario: number,
  data: { fecha: string; cuenta: string }
): Promise<any> {
  return apiPost(`/api/remuneraciones/${idSalario}/adicional/pago-caja`, data);
}


// 18/11/2026: un solo pago para una o varias liquidaciones del mismo empleado.
export interface PagoSocioLiquidacion { idSocio: number; fecha: string; importe: number; medio: "Banco Galicia" | "Banco Nación" | "Otro banco" | "Efectivo del socio" }
export interface PagoCajaLiquidacion { caja: "giamigli-sa" | "campo-chica"; fecha: string; importe: number; cuenta: "A" | "B"; previewVersion?: string; advertenciasAceptadas?: string[] }
export interface TransferenciaLiquidacion { medio: "galicia" | "bna"; id: number; fecha: string; importe: number; detalle: string | null }
export interface PreviewPagoLiquidacion { previewVersion: string; advertencias: string[]; efectosPrevistos: { caja: string; importe: string; saldoResultante: string }[] }
const pagosBase = "/api/remuneraciones/pagos-varios";
export const transferenciasLiquidaciones = (ids: number[]) => apiGet<TransferenciaLiquidacion[]>(`${pagosBase}/transferencias`, { ids: ids.map(String) });
export const pagarLiquidacionesSocio = (ids: number[], d: PagoSocioLiquidacion) => apiPost(`${pagosBase}/socio`, { ...d, idsSalario: ids });
export const pagarLiquidacionesTransferencia = (ids: number[], medio: string, idMovimiento: number) => apiPost(`${pagosBase}/transferencia`, { medio, idMovimiento, idsSalario: ids });
export const previsualizarPagoLiquidaciones = (ids: number[], d: PagoCajaLiquidacion) => apiPost<PreviewPagoLiquidacion>(`${pagosBase}/caja/previsualizar`, { ...d, idsSalario: ids });
export const pagarLiquidacionesCaja = (ids: number[], d: PagoCajaLiquidacion) => apiPost(`${pagosBase}/caja`, { ...d, idsSalario: ids });
