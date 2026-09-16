/**
 * Typed client for the /api/tesoreria contract (see
 * specs/003-tesoreria/contracts/tesoreria-api.md). Each medio keeps its own
 * shape (FR-002) — no unified movimiento type. Read-only except for
 * `validarExcel`, which never persists anything in SQL Server (FR-008) —
 * it only validates and previews an uploaded file, hence it lives outside
 * `apiClient`'s GET-only helper instead of weakening that invariant.
 */

import { API_BASE_URL, apiGet, ApiError } from "@/services/apiClient";

export type Medio =
  | "bna"
  | "galicia"
  | "efectivo"
  | "valores-propios"
  | "valores-recibidos"
  | "tarjetas";

export interface MediosResponse {
  medios: Medio[];
}

export interface MovimientoBNA {
  idMovimientoBNA: number;
  fechaHora: string | null;
  concepto: string | null;
  importe: number | null;
  idContacto: number | null;
  contacto: string | null;
}

export interface MovimientoGalicia {
  idMovimiento: number;
  fecha: string | null;
  descripcion: string | null;
  debitos: number | null;
  creditos: number | null;
  saldo: number | null;
  idContacto: number | null;
  contacto: string | null;
}

export interface PagoEfectivo {
  idPagoEfectivo: number;
  idContacto: number | null;
  fecha: string | null;
  cuenta: string | null;
  caja: string | null;
  numeroDocumento: number | null;
  importeImputado: number | null;
  idOperacion: number | null;
}

export interface ValorPropio {
  idValor: number;
  numeroCheque: number | string | null;
  fechaEmision: string | null;
  fechaVencimiento: string | null;
  importe: number | null;
  cobrado: string | null;
  fechaCobro: string | null;
  numeroCuenta: string | null;
}

export interface ValorRecibido {
  idValor: number;
  numeroValor: number | string | null;
  banco: string | null;
  fechaEmision: string | null;
  fechaVencimiento: string | null;
  fechaCobro: string | null;
  idEmisor: number | null;
  idReceptor: number | null;
  importe: number | null;
  destino: string | null;
}

export interface LineaResumenTarjeta {
  idLineaConsumo: number;
  idResumen: number;
  fechaCompra: string | null;
  detalle: string | null;
  importe: number | null;
  idContacto: number | null;
  numeroDocumento: string | null;
}

export type MovimientoPorMedio = {
  bna: MovimientoBNA;
  galicia: MovimientoGalicia;
  efectivo: PagoEfectivo;
  "valores-propios": ValorPropio;
  "valores-recibidos": ValorRecibido;
  tarjetas: LineaResumenTarjeta;
};

export interface MovimientosResponse<M extends Medio> {
  items: MovimientoPorMedio[M][];
  page: number;
  pageSize: number;
  total: number;
}

export interface MovimientosParams {
  fechaDesde?: string;
  fechaHasta?: string;
  page?: number;
  pageSize?: number;
}

export interface CompraCandidata {
  idCompra: number;
  numeroDocumento: string | null;
  proveedor: string | null;
  fecha: string | null;
  importe: number | null;
}

export interface ReferenciaOrigen {
  estado: "sin_coincidencia" | "coincidencia_unica" | "ambigua";
  candidatas: CompraCandidata[];
}

export function fetchMedios(): Promise<MediosResponse> {
  return apiGet<MediosResponse>("/api/tesoreria/medios");
}

export function fetchMovimientos<M extends Medio>(
  medio: M,
  params: MovimientosParams
): Promise<MovimientosResponse<M>> {
  return apiGet<MovimientosResponse<M>>(`/api/tesoreria/${medio}/movimientos`, { ...params });
}

export function fetchReferenciaOrigen(
  medio: Medio,
  idMovimiento: number
): Promise<ReferenciaOrigen> {
  return apiGet<ReferenciaOrigen>(
    `/api/tesoreria/${medio}/movimientos/${idMovimiento}/referencia`
  );
}

export interface ExcelValidacionResponse {
  medioDetectado: "bna" | "galicia" | null;
  valido: boolean;
  errores: string[];
  movimientosPrevisualizados: Record<string, unknown>[];
}

export async function validarExcel(archivo: File): Promise<ExcelValidacionResponse> {
  const formData = new FormData();
  formData.append("archivo", archivo);

  const response = await fetch(new URL("/api/tesoreria/excel/validar", API_BASE_URL), {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new ApiError(response.status, detail || response.statusText);
  }

  return (await response.json()) as ExcelValidacionResponse;
}
