/**
 * Resúmenes de tarjeta (Historia 1) — ver
 * specs/008-tarjetas/contracts/tarjetas-api.md. Escribe exclusivamente
 * contra `WC`.
 */

import { apiDelete, apiGet, apiPost, apiPut } from "@/services/apiClient";

export interface LineaConsumoInput {
  fechaCompra: string;
  detalle: string;
  importe: number;
  fechaVencimientoCompra?: string | null;
  idContacto?: number | null;
  nroDocumento?: string | null;
}

export interface CompraVinculada {
  idVinculo: number;
  idCompra: number;
  proveedor: string | null;
  tipoDocumento: string | null;
  numeroDocumento: string | null;
  fechaCompra: string | null;
  importeCompra: number | null;
  importeImputado: number;
}

export interface LineaConsumo extends LineaConsumoInput {
  idLineaConsumo: number | null;
  comprasVinculadas: CompraVinculada[];
}

export interface PagoResumen {
  idPago: number;
  fecha: string;
  importe: number;
  origen: string | null;
  idMovimientoOrigen: number | null;
}

export interface ResumenAltaInput {
  idTarjeta: number;
  codigo: string;
  fechaCierre: string;
  fechaVencimiento: string;
  urlResumenOriginal?: string | null;
  impuestoSellos?: number;
  gastosAdmin?: number;
  mantCuenta?: number;
  renovAnual?: number;
  promocionBNA?: number;
  creditoContingente?: number;
  intFinanc?: number;
  intCompens?: number;
  iva105?: number;
  percepIVA105?: number;
  iva21?: number;
  percepIVA21?: number;
  percepIIBB?: number;
  ajusteResAnterior?: number;
  lineas: LineaConsumoInput[];
}

export interface ResumenDetalle extends ResumenAltaInput {
  idResumen: number;
  tarjeta: string | null;
  totalCalculado: number;
  lineas: LineaConsumo[];
  pagos: PagoResumen[];
  warnings: string[];
}

export interface ResumenListItem {
  idResumen: number;
  idTarjeta: number;
  tarjeta: string | null;
  codigo: string;
  fechaCierre: string | null;
  fechaVencimiento: string | null;
  urlResumenOriginal: string | null;
  totalCalculado: number;
  soloCabecera: boolean;
  pagoConciliado: boolean;
  /** totalCalculado - pagado, con signo — nunca oculta (ver research.md, tolerancia $0.10). */
  diferenciaRedondeo: number;
  lineasTotal: number;
  lineasVinculadas: number;
}

export interface ResumenesListResponse {
  items: ResumenListItem[];
  page: number;
  pageSize: number;
  total: number;
}

export function fetchResumenes(params: {
  idTarjeta?: number;
  fechaCierreDesde?: string;
  fechaCierreHasta?: string;
  fechaVencimientoDesde?: string;
  fechaVencimientoHasta?: string;
  page?: number;
  pageSize?: number;
}): Promise<ResumenesListResponse> {
  return apiGet<ResumenesListResponse>("/api/tarjetas-resumenes", { ...params });
}

export function fetchResumenDetalle(idResumen: number): Promise<ResumenDetalle> {
  return apiGet<ResumenDetalle>(`/api/tarjetas-resumenes/${idResumen}`);
}

export function crearResumen(input: ResumenAltaInput): Promise<ResumenDetalle> {
  return apiPost<ResumenDetalle>("/api/tarjetas-resumenes", input);
}

export function actualizarResumen(idResumen: number, input: ResumenAltaInput, lockToken: string): Promise<ResumenDetalle> {
  return apiPut<ResumenDetalle>(`/api/tarjetas-resumenes/${idResumen}`, input, { "X-Lock-Token": lockToken });
}

export function eliminarResumen(idResumen: number, lockToken: string): Promise<void> {
  return apiDelete(`/api/tarjetas-resumenes/${idResumen}`, { "X-Lock-Token": lockToken });
}

export interface LockResumenResponse {
  idResumen: number;
  lockToken: string;
  expiresAt: string;
}

export function adquirirLockResumen(idResumen: number, lockToken: string, force = false): Promise<LockResumenResponse> {
  return apiPost<LockResumenResponse>(`/api/tarjetas-resumenes/${idResumen}/lock`, { lockToken, force });
}

export function liberarLockResumen(idResumen: number, lockToken: string, keepalive = false): Promise<void> {
  return apiDelete(`/api/tarjetas-resumenes/${idResumen}/lock`, { "X-Lock-Token": lockToken }, keepalive);
}

// --- Punto 4 del feedback (2026-09-19): vínculo línea de consumo -> Compras reales ---

export function vincularCompra(
  idLineaConsumo: number,
  idCompra: number,
  importeImputado: number
): Promise<CompraVinculada> {
  return apiPost<CompraVinculada>(`/api/tarjetas-resumenes/lineas/${idLineaConsumo}/compras`, {
    idCompra,
    importeImputado,
  });
}

export function quitarVinculoCompra(idLineaConsumo: number, idVinculo: number): Promise<void> {
  return apiDelete(`/api/tarjetas-resumenes/lineas/${idLineaConsumo}/compras/${idVinculo}`);
}

// --- Punto 6 del feedback (2026-09-19): pagos de un resumen ---

export function fetchPagosResumen(idResumen: number): Promise<PagoResumen[]> {
  return apiGet<PagoResumen[]>(`/api/tarjetas-resumenes/${idResumen}/pagos`);
}

export function registrarPagoResumen(
  idResumen: number,
  input: { fecha: string; importe: number; origen?: string | null; idMovimientoOrigen?: number | null }
): Promise<PagoResumen> {
  return apiPost<PagoResumen>(`/api/tarjetas-resumenes/${idResumen}/pagos`, input);
}

export function eliminarPagoResumen(idResumen: number, idPago: number): Promise<void> {
  return apiDelete(`/api/tarjetas-resumenes/${idResumen}/pagos/${idPago}`);
}

// --- Conciliación de una línea contra documentos (pesificados, uno o varios) ---

export interface DocumentoCandidato {
  idCompra: number;
  fecha: string | null;
  tipoDocumento: string | null;
  numeroDocumento: string | null;
  moneda: string | null;
  tipoDeCambio: number | null;
  /** Importe en la moneda del documento; las Notas de Crédito vienen negativas. */
  importeOriginal: number;
  /** Importe pesificado con el tipo de cambio propio del documento. */
  importePesos: number;
  proveedor: string | null;
  /** Cuántas otras líneas de consumo ya usan este documento (ej. cuotas). */
  vinculosPrevios: number;
}

export interface ConciliacionCalculo {
  /** exacta: en pesos y dentro de $0,10 · aproximada: en dólares con TC implícito cercano al del documento · parcial: no cierra. */
  estado: "exacta" | "aproximada" | "parcial";
  diferencia: number;
  pagoParcial: boolean;
  tcImplicito: number | null;
  tcReferencia: number | null;
  desvioTc: number | null;
  imputados: { idCompra: number; importeImputado: number }[];
}

export interface SugerenciaConciliacion extends ConciliacionCalculo {
  idsCompra: number[];
}

export interface CandidatosLinea {
  idLineaConsumo: number;
  importeLinea: number;
  fechaLinea: string | null;
  idContacto: number | null;
  documentos: DocumentoCandidato[];
  sugerencias: SugerenciaConciliacion[];
}

export interface ConciliacionPreview extends ConciliacionCalculo {
  documentos: DocumentoCandidato[];
}

export function fetchCandidatosLinea(idLineaConsumo: number): Promise<CandidatosLinea> {
  return apiGet<CandidatosLinea>(`/api/tarjetas-resumenes/lineas/${idLineaConsumo}/candidatos`);
}

export function fetchConciliacionPreview(idLineaConsumo: number, idsCompra: number[]): Promise<ConciliacionPreview> {
  return apiGet<ConciliacionPreview>(`/api/tarjetas-resumenes/lineas/${idLineaConsumo}/conciliacion`, {
    idsCompra: idsCompra.map(String),
  });
}

export function vincularComprasLote(idLineaConsumo: number, idsCompra: number[]): Promise<CompraVinculada[]> {
  return apiPost<CompraVinculada[]>(`/api/tarjetas-resumenes/lineas/${idLineaConsumo}/compras/lote`, { idsCompra });
}
