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
  /** "SinDocumento" | "DiferenciaAceptada" cuando se resolvió a mano (009). */
  estadoLinea?: string | null;
  motivoEstado?: string | null;
  detalleEstado?: string | null;
  importeDiferencia?: number | null;
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
  /** Nota de crédito/débito que ajusta el tipo de cambio de una factura en dólares. */
  ajustaTipoCambio: boolean;
}

export interface ConciliacionCalculo {
  /** exacta: cierra en pesos (±$0,10; ±$1 con dólares) · parcial: no cierra. */
  estado: "exacta" | "parcial";
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

export interface LineaContexto {
  idLineaConsumo: number;
  idResumen: number;
  resumenCodigo: string | null;
  tarjeta: string | null;
  fechaCompra: string | null;
  detalle: string | null;
  importe: number;
  idContacto: number | null;
  proveedor: string | null;
  nroDocumento: string | null;
  urlResumenOriginal: string | null;
}

export interface LineaHermana {
  idLineaConsumo: number;
  idResumen: number;
  resumenCodigo: string | null;
  fechaCompra: string | null;
  detalle: string | null;
  importe: number;
}

export interface EstadoLinea {
  idLineaConsumo: number;
  estado: string;
  motivo: string;
  detalle: string | null;
  importeDiferencia: number | null;
}

export interface CandidatosLinea {
  idLineaConsumo: number;
  importeLinea: number;
  fechaLinea: string | null;
  idContacto: number | null;
  linea: LineaContexto;
  estado: EstadoLinea | null;
  hermanas: LineaHermana[];
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

export interface AceptarDiferencia {
  motivo: string;
  detalle?: string | null;
}

export function vincularComprasLote(
  idLineaConsumo: number,
  idsCompra: number[],
  aceptarDiferencia?: AceptarDiferencia | null
): Promise<CompraVinculada[]> {
  return apiPost<CompraVinculada[]>(`/api/tarjetas-resumenes/lineas/${idLineaConsumo}/compras/lote`, {
    idsCompra,
    aceptarDiferencia: aceptarDiferencia ?? null,
  });
}

export const MOTIVOS_DIFERENCIA: { value: string; label: string }[] = [
  { value: "AjusteTipoCambioSinNota", label: "Ajuste de tipo de cambio sin nota" },
  { value: "Redondeo", label: "Redondeo" },
  { value: "Otro", label: "Otro (indicar detalle)" },
];

export const MOTIVOS_SIN_DOCUMENTO: { value: string; label: string }[] = [
  { value: "Impuesto", label: "Impuesto" },
  { value: "Interes", label: "Interés" },
  { value: "CompraNoCargada", label: "Compra no cargada en el sistema" },
  { value: "Otro", label: "Otro (indicar detalle)" },
];

export function etiquetaMotivo(motivo: string): string {
  return [...MOTIVOS_DIFERENCIA, ...MOTIVOS_SIN_DOCUMENTO].find((m) => m.value === motivo)?.label ?? motivo;
}

export function marcarSinDocumento(idLineaConsumo: number, motivo: string, detalle?: string | null): Promise<void> {
  return apiPost<void>(`/api/tarjetas-resumenes/lineas/${idLineaConsumo}/sin-documento`, {
    motivo,
    detalle: detalle ?? null,
  });
}

export function quitarEstadoLinea(idLineaConsumo: number): Promise<void> {
  return apiDelete(`/api/tarjetas-resumenes/lineas/${idLineaConsumo}/estado`);
}

export function buscarDocumentos(q: string): Promise<DocumentoCandidato[]> {
  return apiGet<DocumentoCandidato[]>("/api/tarjetas-resumenes/documentos-buscar", { q });
}

// --- Bandeja de pendientes ---

export interface DocumentoResumido {
  idCompra: number;
  tipoDocumento: string | null;
  numeroDocumento: string | null;
  moneda: string | null;
  importeOriginal: number;
  importePesos: number;
  proveedor: string | null;
}

export interface LineaPendiente {
  idLineaConsumo: number;
  idResumen: number;
  resumenCodigo: string | null;
  idTarjeta: number;
  tarjeta: string | null;
  fechaCierre: string | null;
  fechaCompra: string | null;
  detalle: string | null;
  importe: number;
  idContacto: number | null;
  proveedor: string | null;
  nroDocumento: string | null;
  urlResumenOriginal: string | null;
  cantidadDocumentos: number;
  sugerencia: { idsCompra: number[]; estado: string; unica: boolean; documentos: DocumentoResumido[] } | null;
}

export interface PendientesResponse {
  items: LineaPendiente[];
  page: number;
  pageSize: number;
  total: number;
  totalConSugerencia: number;
}

export interface FiltrosPendientes {
  idTarjeta?: string;
  proveedor?: string;
  fechaCierreDesde?: string;
  fechaCierreHasta?: string;
  soloConSugerencia?: boolean;
  page: number;
  pageSize: number;
}

export function fetchPendientes(f: FiltrosPendientes): Promise<PendientesResponse> {
  return apiGet<PendientesResponse>("/api/tarjetas-resumenes/pendientes", {
    idTarjeta: f.idTarjeta,
    proveedor: f.proveedor,
    fechaCierreDesde: f.fechaCierreDesde,
    fechaCierreHasta: f.fechaCierreHasta,
    soloConSugerencia: f.soloConSugerencia ? "true" : undefined,
    page: f.page,
    pageSize: f.pageSize,
  });
}

export interface ExactaPropuesta {
  idLineaConsumo: number;
  resumenCodigo: string | null;
  tarjeta: string | null;
  fechaCompra: string | null;
  detalle: string | null;
  proveedor: string | null;
  importe: number;
  documentos: DocumentoResumido[];
}

export function fetchExactasPropuestas(): Promise<ExactaPropuesta[]> {
  return apiGet<ExactaPropuesta[]>("/api/tarjetas-resumenes/pendientes/exactas");
}

export function aceptarExactas(idsLineas: number[]): Promise<{ aplicadas: number; omitidas: number[] }> {
  return apiPost("/api/tarjetas-resumenes/pendientes/aceptar-exactas", { idsLineas });
}

// --- Reparto muchas líneas x muchos documentos ---

export interface RepartoItem {
  idLinea: number;
  idCompra: number;
  importe: number;
}

export interface RepartoPropuesta {
  lineas: { idLinea: number; importe: number; fechaCompra: string | null }[];
  documentos: DocumentoCandidato[];
  reparto: RepartoItem[];
  diferencias: Record<string, number>;
}

export function proponerReparto(idsLineas: number[], idsCompra: number[]): Promise<RepartoPropuesta> {
  return apiPost<RepartoPropuesta>("/api/tarjetas-resumenes/lineas/reparto-propuesta", { idsLineas, idsCompra });
}

export function conciliarReparto(
  reparto: RepartoItem[],
  aceptarDiferencia?: AceptarDiferencia | null
): Promise<{ lineas: number; vinculos: number }> {
  return apiPost("/api/tarjetas-resumenes/lineas/conciliar-reparto", {
    reparto,
    aceptarDiferencia: aceptarDiferencia ?? null,
  });
}
