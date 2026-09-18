/**
 * Typed client for the /api/compras contract. La lectura (spec 002) es
 * GET-only; desde 006-carga-compras (`contracts/compras-alta-api.md`) se
 * agregan alta/edición, que escriben exclusivamente contra `WC` (ver nota
 * en `apiClient.ts`).
 */

import { API_BASE_URL, apiDelete, apiGet, apiPost, apiPut } from "@/services/apiClient";
import type { TipoContacto } from "@/services/contactosApi";

/** Tipos de contacto válidos como proveedor de una compra (`validar_compra`
 * en el backend, `repository.py`) — no solo "Proveedor". Restringir el
 * combo a un único tipo dejaba fuera contactos válidos y, peor, hacía que
 * compitieran por los primeros N resultados de búsqueda con tipos que ni
 * siquiera son seleccionables acá (Comprador, Consignatario, etc.). */
export const TIPOS_CONTACTO_COMPRA: TipoContacto[] = [
  "Proveedor",
  "Multiple",
  "Organismo",
  "Empleado",
  "Banco",
];

/** URL del PDF servido desde el disco local de esta PC (ver
 * `GET /api/compras/documento-local` — el backend corre en la misma
 * máquina que el archivo, así el navegador sí puede mostrarlo). */
export function urlDocumentoLocal(ruta: string): string {
  const url = new URL("/api/compras/documento-local", API_BASE_URL);
  url.searchParams.set("ruta", ruta);
  return url.toString();
}

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
  /** Importe total del documento (`vw_Compras_ImporteDocumento`) — ver
   * uso en el buscador manual de facturas de Tarjetas (008). */
  importeDocumento: number | null;
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

export interface VencimientoCompra {
  idVencimiento: number;
  fechaVencimiento: string | null;
}

export interface CompraDetalle {
  idCompra: number;
  fecha: string | null;
  proveedor: Proveedor | null;
  tipo: string | null;
  tipoDocumento: string | null;
  numeroDocumento: string | null;
  moneda: string | null;
  tipoDeCambio: number | null;
  conceptosNoGravados: number | null;
  ingresosBrutos: number | null;
  guias: number | null;
  comision: number | null;
  financiacion: number | null;
  gastosVarios: number | null;
  leyDeSellos: number | null;
  resGral4169: number | null;
  ajustaTipoCambio: boolean | null;
  documentoOriginal: string | null;
  lineas: LineaCompra[];
  vencimientos: VencimientoCompra[];
}

export interface ComprasSearchParams {
  proveedor?: string;
  numeroDocumento?: string;
  fechaDesde?: string;
  fechaHasta?: string;
  idCentroCosto?: number;
  idRubro?: number;
  /** Filtro exacto — usado para listar los documentos relacionados de un proveedor (006). */
  idContacto?: number;
  /** Filtro exacto (repetible) — usado para acotar a tipos de documento complementarios (006). */
  tipoDocumento?: string[];
  productoServicio?: string;
  idDestino?: number;
  campania?: string;
  sortBy?: string;
  sortDir?: "asc" | "desc";
  page?: number;
  pageSize?: number;
}

export function fetchCompras(
  params: ComprasSearchParams
): Promise<ComprasListResponse> {
  return apiGet<ComprasListResponse>("/api/compras", { ...params });
}

export interface CentroCosto {
  idCentroCosto: number;
  centroCosto: string | null;
}

export interface Rubro {
  idRubro: number;
  rubro: string | null;
}

export interface Destino {
  idDestino: number;
  destino: string | null;
}

export interface UnidadMedida {
  unidad: string;
}

export interface Campania {
  idCampania: number;
  campania: string | null;
}

export interface FiltrosComprasResponse {
  centrosCosto: CentroCosto[];
  rubros: Rubro[];
  destinos: Destino[];
  unidadesMedida: UnidadMedida[];
  campañas: Campania[];
}

/** Catálogos para los filtros — replica los combos del Frm Listado Compras real. */
export function fetchFiltrosCompras(): Promise<FiltrosComprasResponse> {
  return apiGet<FiltrosComprasResponse>("/api/compras/filtros");
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

// --- Alta/edición (006-carga-compras) — escriben exclusivamente contra `WC` ---

export type TipoComprobante = "A" | "B" | "C" | "M" | "X";
export type TipoDocumentoCompra =
  | "Factura"
  | "Nota de Crédito"
  | "Nota de Débito"
  | "C. Deposito Cereales";
export type MonedaCompra = "Pesos" | "Dolares";

export interface LineaInput {
  productoServicio: string;
  cantidad: number;
  precioUnitario: number;
  iva: number;
  unidad?: string | null;
  idCentroCosto?: number | null;
  idDestino?: number | null;
  idRubro?: number | null;
  campaña?: string | null;
  ajusteFinanciero?: boolean;
}

export interface VencimientoInput {
  fechaVencimiento: string;
}

export interface CompraAltaInput {
  idContacto: number;
  fecha: string;
  tipo: TipoComprobante;
  tipoDocumento: TipoDocumentoCompra;
  numeroDocumento: string;
  moneda: MonedaCompra;
  tipoDeCambio?: number | null;
  ingresosBrutos?: number;
  conceptosNoGravados?: number;
  guias?: number;
  comision?: number;
  financiacion?: number;
  gastosVarios?: number;
  leyDeSellos?: number;
  resGral4169?: number;
  ajustaTipoCambio?: boolean;
  documentoOriginal?: string | null;
  lineas: LineaInput[];
  vencimientos: VencimientoInput[];
}

export interface PesificadoBlock {
  subtotalNeto: number;
  ivaCabecera: number;
  importeTotal: number;
}

export interface LineaCalculada extends LineaInput {
  idDetalleCompra: number | null;
  subtotal: number;
  importeIva: number;
}

export interface VencimientoCalculado extends VencimientoInput {
  idVencimiento: number | null;
}

export interface CompraDetalleCompleto extends CompraAltaInput {
  idCompra: number;
  subtotalNeto: number;
  ivaCabecera: number;
  importeTotal: number;
  pesificado: PesificadoBlock | null;
  lineas: LineaCalculada[];
  vencimientos: VencimientoCalculado[];
  warnings: string[];
}

/** Alta de una compra completa (cabecera + líneas + vencimientos). Escribe solo en `WC`. */
export function crearCompra(input: CompraAltaInput): Promise<CompraDetalleCompleto> {
  return apiPost<CompraDetalleCompleto>("/api/compras", input);
}

/** Edición: reemplaza cabecera+líneas+vencimientos por completo. Requiere el lock adquirido. */
export function actualizarCompra(
  idCompra: number,
  input: CompraAltaInput,
  lockToken: string
): Promise<CompraDetalleCompleto> {
  return apiPut<CompraDetalleCompleto>(`/api/compras/${idCompra}`, input, {
    "X-Lock-Token": lockToken,
  });
}

/** Eliminación definitiva (documento cargado por error). Requiere el lock adquirido. */
export function eliminarCompra(idCompra: number, lockToken: string): Promise<void> {
  return apiDelete(`/api/compras/${idCompra}`, { "X-Lock-Token": lockToken });
}

export interface LockResponse {
  idCompra: number;
  lockToken: string;
  expiresAt: string;
}

/** Adquiere o renueva el bloqueo exclusivo de edición (FR-009a). 409 si otra sesión lo tiene.
 * `force` ("Forzar edición" en el error de bloqueo — sistema de un solo
 * usuario real, ver `repository_locks.py`) ignora un lock vigente de otro
 * token, para el caso de una pestaña vieja del mismo usuario colgada. */
export function adquirirLock(
  idCompra: number,
  lockToken: string,
  force = false
): Promise<LockResponse> {
  return apiPost<LockResponse>(`/api/compras/${idCompra}/lock`, { lockToken, force });
}

/** Libera el bloqueo. 409 si pertenece a otra sesión. `keepalive` para
 * liberarlo de forma confiable al cerrar la pestaña (ver `apiDelete`). */
export function liberarLock(idCompra: number, lockToken: string, keepalive = false): Promise<void> {
  return apiDelete(`/api/compras/${idCompra}/lock`, { "X-Lock-Token": lockToken }, keepalive);
}

export interface RubroSugerido {
  idRubro: number | null;
  rubro: string | null;
  frecuencia: number;
}

/** FR-012a: sugerencia no vinculante — el usuario siempre puede cambiarla. */
export function fetchRubroSugerido(productoServicio: string): Promise<RubroSugerido> {
  return apiGet<RubroSugerido>("/api/compras/rubro-sugerido", { productoServicio });
}

// --- Alta controlada de catálogos: los combos de línea (Rubro/Centro de
// Costos/Destino/Campaña) no admiten texto libre — agregar un valor nuevo
// pasa por una confirmación explícita del usuario antes de llamar a estas
// funciones (evita duplicados por error de tipeo). Escriben solo en `WC`.

export function crearRubro(nombre: string): Promise<Rubro> {
  return apiPost<Rubro>("/api/compras/rubros", { nombre });
}

export function crearCentroCosto(nombre: string): Promise<CentroCosto> {
  return apiPost<CentroCosto>("/api/compras/centros-costo", { nombre });
}

export function crearDestino(nombre: string): Promise<Destino> {
  return apiPost<Destino>("/api/compras/destinos", { nombre });
}

export function crearCampania(nombre: string): Promise<Campania> {
  return apiPost<Campania>("/api/compras/campanias", { nombre });
}

// --- Documentos relacionados: vínculo manual entre documentos (ej. una Nota
// de Crédito/Débito que complementa una Factura), para referencia futura —
// no es un listado automático de todo lo comprado al proveedor. ---

export interface DocumentoRelacionado {
  idCompra: number;
  fecha: string | null;
  tipoDocumento: string | null;
  numeroDocumento: string | null;
}

export function fetchDocumentosRelacionados(idCompra: number): Promise<DocumentoRelacionado[]> {
  return apiGet<DocumentoRelacionado[]>(`/api/compras/${idCompra}/relacionados`);
}

export function agregarDocumentoRelacionado(idCompra: number, idCompraRelacionada: number): Promise<void> {
  return apiPost(`/api/compras/${idCompra}/relacionados`, { idCompraRelacionada });
}

export function quitarDocumentoRelacionado(idCompra: number, idCompraRelacionada: number): Promise<void> {
  return apiDelete(`/api/compras/${idCompra}/relacionados/${idCompraRelacionada}`);
}
