/**
 * Auditoría de cuentas corrientes — 035-auditoria-cuentas-proveedores.
 * Ver specs/035-auditoria-cuentas-proveedores/contracts/auditoria-cuentas-api.md.
 */

import { apiDelete, apiGet, apiPost, apiPut } from "@/services/apiClient";
import type { Origen } from "@/services/cuentasCorrientesApi";

export type CausaCuenta =
  | "coincide"
  | "coincide-causa-conocida"
  | "diferencia-menor-umbral"
  | "fuera-de-plazo-decidido"
  | "aplicacion-fuera-de-plazo"
  | "doble-descuento-tarjeta"
  | "nota-sin-imputar"
  | "impuesto-sin-boleta"
  | "movimiento-sin-contacto"
  | "sobrepago"
  | "contacto-duplicado"
  | "falta-documento"
  | "sin-referencia"
  | "otros";

export interface ParametrosAuditoria {
  plazoMaximoMeses: number;
  umbralPesos: number;
  anticipoDias: number;
}

export interface CausaResumen {
  causa: CausaCuenta;
  cuentas: number;
  importe: number;
  excepcion: boolean;
  /** Imputaciones sospechosas: la cuenta puede estar aquí aunque su saldo coincida con el Access. */
  adicional: boolean;
  /** Solo en movimiento-sin-contacto: se cuentan movimientos y no cuentas. */
  movimientos?: number;
}

export interface ResumenAuditoria {
  fechaCorte: string;
  parametros: ParametrosAuditoria;
  totalCuentas: number;
  coinciden: number;
  conDiferencia: number;
  causas: CausaResumen[];
  avisoCorte: string;
}

export interface CuentaAuditada {
  idContacto: number;
  razonSocial: string | null;
  moneda: string;
  saldoSistema: number;
  saldoAccess: number | null;
  diferencia: number | null;
  sinExplicar: number;
  causa: CausaCuenta;
  componentes: Record<string, number>;
  hallazgos: number;
  causasExtra: CausaCuenta[];
  /** Motivo con el que Sergio documentó la diferencia de esta cuenta. */
  documentada?: string | null;
}

export interface GrupoCuentas {
  causa: CausaCuenta;
  items: CuentaAuditada[];
  total: number;
  conceptos?: ConceptoSinContacto[];
  explicados?: { clave: string; movimientos: number; importe: number }[];
}

export interface Hallazgo {
  causa: string;
  motivo: string;
  importe: number | null;
  medio?: string | null;
  idMovimiento?: number | null;
  fechaPago?: string | null;
  cantidadFacturas?: number | null;
  facturaMasVieja?: string | null;
  diasMaximos?: number | null;
  origenAplicacion?: string | null;
  idsAplicacion?: number[];
}

export interface HallazgosCuenta {
  idContacto: number;
  razonSocial: string | null;
  hallazgos: Hallazgo[];
}

export function fetchResumenAuditoria(): Promise<ResumenAuditoria> {
  return apiGet<ResumenAuditoria>("/api/auditoria-cuentas/resumen");
}

export function fetchGrupo(causa: CausaCuenta, pagina = 1, tamano = 100): Promise<GrupoCuentas> {
  return apiGet<GrupoCuentas>(`/api/auditoria-cuentas/grupos/${causa}`, { pagina, tamano });
}

export function fetchHallazgos(idContacto: number): Promise<HallazgosCuenta> {
  return apiGet<HallazgosCuenta>(`/api/auditoria-cuentas/cuentas/${idContacto}/hallazgos`);
}

export function fetchParametros(): Promise<ParametrosAuditoria> {
  return apiGet<ParametrosAuditoria>("/api/auditoria-cuentas/parametros");
}

export function guardarParametros(cambios: Partial<ParametrosAuditoria>): Promise<ParametrosAuditoria> {
  return apiPut<ParametrosAuditoria>("/api/auditoria-cuentas/parametros", cambios);
}

export interface ConceptoSinContacto {
  concepto: string;
  movimientos: number;
  importe: number;
  neto: number;
  ejemplos: { medio: string; idMovimiento: number; fecha: string | null; importe: number; concepto: string | null }[];
}

export interface Conocido {
  idConocido: number;
  tipo: "concepto-movimiento" | "cuenta";
  clave: string;
  importeRef: number | null;
  motivo: string;
  usuario: string | null;
  activo: boolean;
}

export function fetchConocidos(): Promise<Conocido[]> {
  return apiGet<Conocido[]>("/api/auditoria-cuentas/conocidos");
}

export function crearConocido(alta: { tipo: Conocido["tipo"]; clave: string; motivo: string; importeRef?: number }): Promise<Conocido> {
  return apiPost<Conocido>("/api/auditoria-cuentas/conocidos", alta);
}

export function darDeBajaConocido(idConocido: number): Promise<void> {
  return apiDelete(`/api/auditoria-cuentas/conocidos/${idConocido}`);
}

// ---- Revisión de una cuenta ------------------------------------------------

export type EstadoRevision = "pendiente" | "revisada" | "revision-vieja";

export interface SugerenciaNota {
  tipo: "credito" | "debito";
  importe: number;
  moneda: "Pesos" | "Dolares";
  tipoDeCambio: number | null;
}

export interface AvisoCuenta {
  tipo: string;
  motivo: string;
  importe: number | null;
  sugerencia?: SugerenciaNota | null;
}

export interface CuentaVecina {
  idContacto: number;
  razonSocial: string | null;
}

export interface EntradaHistorial {
  id: number;
  accion: string;
  detalle: string | null;
  usuario: string | null;
  fecha: string | null;
}

export interface RevisionCuenta {
  idContacto: number;
  razonSocial: string | null;
  moneda: string;
  saldo: number;
  gobierna?: "Pesos" | "Dolares" | "Mixta";
  saldoEsperado: "cero" | "puede-tener-saldo" | null;
  estado: EstadoRevision;
  fechaRevision: string | null;
  usuarioRevision: string | null;
  nota: string | null;
  saldoAlRevisar: number | null;
  dificultad: 0 | 1 | 2;
  avisos: AvisoCuenta[];
  siguiente: CuentaVecina | null;
  anterior: CuentaVecina | null;
  revisadas: number;
  totalCuentas: number;
  historial: EntradaHistorial[];
}

export function fetchRevision(idContacto: number, refrescar = false): Promise<RevisionCuenta> {
  return apiGet<RevisionCuenta>(`/api/auditoria-cuentas/cuentas/${idContacto}/revision`, { refrescar: refrescar ? "true" : undefined });
}

export function guardarRevision(
  idContacto: number,
  cambio: { estado?: "pendiente" | "revisada"; nota?: string; saldoEsperado?: "cero" | "puede-tener-saldo"; quitarSaldoEsperado?: boolean }
): Promise<RevisionCuenta> {
  return apiPut<RevisionCuenta>(`/api/auditoria-cuentas/cuentas/${idContacto}/revision`, cambio);
}

export function fetchPrimeraPendiente(despuesDe?: number): Promise<CuentaVecina | null> {
  return apiGet<CuentaVecina | null>("/api/auditoria-cuentas/revision/siguiente", { despuesDe });
}

export function fetchComprobantes(idContacto: number): Promise<Record<string, string>> {
  return apiGet<Record<string, string>>(`/api/auditoria-cuentas/cuentas/${idContacto}/comprobantes`);
}

export interface CorreccionCuenta {
  idCorreccion: number;
  regla: string;
  estado: string;
  usuario: string | null;
  fecha: string | null;
  detalle: string | null;
}

export function anularImputaciones(idContacto: number, idsAplicacion: number[], motivo: string): Promise<{ idCorreccion: number; aplicaciones: number; importe: number }> {
  return apiPost(`/api/auditoria-cuentas/cuentas/${idContacto}/anular-aplicaciones`, { idsAplicacion, motivo });
}

export function revertirCorreccion(idCorreccion: number): Promise<{ idCorreccion: number; aplicaciones: number }> {
  return apiPost(`/api/auditoria-cuentas/correcciones/${idCorreccion}/revertir`, {});
}

export function fetchCorrecciones(idContacto: number): Promise<CorreccionCuenta[]> {
  return apiGet<CorreccionCuenta[]>(`/api/auditoria-cuentas/cuentas/${idContacto}/correcciones`);
}

export function cargarNotaAjuste(
  idContacto: number,
  nota: { tipo: "debito" | "credito"; fecha: string; importe: number; moneda: "Pesos" | "Dolares"; tipoDeCambio?: number; motivo: string }
): Promise<{ idCompra: number }> {
  return apiPost(`/api/auditoria-cuentas/cuentas/${idContacto}/nota-ajuste`, nota);
}

// ---- Movimientos con un solo criterio de moneda -----------------------------------

export interface MovimientoRevision {
  fecha: string | null;
  documento: string | null;
  numeroDocumento: string | null;
  /** Moneda del documento. Los pagos y cobros son siempre en pesos. */
  moneda: "Pesos" | "Dolares";
  deudaOriginal: number;
  creditoOriginal: number;
  tipoDeCambio: number | null;
  tcEstimado: boolean;
  /** Fecha en que se entregó el cheque con el que se pagó (el dólar se toma de ese día). */
  fechaEntrega: string | null;
  deudaPesos: number;
  creditoPesos: number;
  saldoPesos: number;
  saldoDolares: number;
  origen: Origen;
  origenTipo: string | null;
  idOrigen: number | null;
}

export interface MovimientosRevision {
  items: MovimientoRevision[];
  total: number;
  page: number;
  pageSize: number;
  saldoPesos: number;
  saldoDolares: number;
  tieneDolares: boolean;
  bimonetaria: boolean;
  /** Moneda que gobierna: Dolares si todos sus documentos están en dólares, Pesos si ninguno, Mixta si tiene de las dos. */
  gobierna: "Pesos" | "Dolares" | "Mixta";
  saldoGobierna: number;
  avisos: string[];
}

export function fetchMovimientosRevision(idContacto: number, page: number, pageSize = 100, refrescar = false): Promise<MovimientosRevision> {
  return apiGet<MovimientosRevision>(`/api/auditoria-cuentas/cuentas/${idContacto}/movimientos`, { page, pageSize, refrescar: refrescar ? "true" : undefined });
}

// ---- Recalcular las imputaciones de una cuenta (FIFO) -------------------------

export interface ResultadoFifo {
  idEjecucion: number;
  contacto: {
    facturadoAntes: number;
    pagadoAntes: number;
    aplicadoAntes: number;
    aplicadoDespues: number;
    anticipoAbierto: number;
    saldo: number;
    cerrabaAntes: boolean;
    cierraDespues: boolean;
    tendencia: "mejora" | "igual" | "empeora";
    marcas: { codigo: string; descripcion: string }[];
  };
  aplicaciones: number;
  aplicacionesVigentes: number;
}

export function simularFifo(idContacto: number): Promise<ResultadoFifo> {
  return apiPost<ResultadoFifo>(`/api/auditoria-cuentas/cuentas/${idContacto}/fifo/simular`, {});
}

export function aplicarFifo(idContacto: number, idEjecucion: number): Promise<{ aplicados: number[]; sinCambios: number[]; backup: string }> {
  return apiPost(`/api/auditoria-cuentas/cuentas/${idContacto}/fifo/${idEjecucion}/aplicar`, {});
}

export function revertirFifo(idContacto: number, idEjecucion: number): Promise<unknown> {
  return apiPost(`/api/auditoria-cuentas/cuentas/${idContacto}/fifo/${idEjecucion}/revertir`, {});
}

// ---- Asignar contacto a movimientos del banco sin contacto ---------------------------

export interface MovimientoSinContacto {
  medio: "bna" | "galicia";
  idMovimiento: number;
  fecha: string | null;
  importe: number;
  concepto: string | null;
}

export function fetchMovimientosSinContacto(concepto?: string, limite = 300): Promise<MovimientoSinContacto[]> {
  return apiGet<MovimientoSinContacto[]>("/api/auditoria-cuentas/movimientos-sin-contacto", { concepto, limite });
}

export function asignarContacto(
  items: { medio: string; idMovimiento: number }[],
  idContacto: number,
  motivo: string
): Promise<{ idCorreccion: number; movimientos: number; contacto: string }> {
  return apiPost("/api/auditoria-cuentas/movimientos-sin-contacto/asignar", { items, idContacto, motivo });
}
