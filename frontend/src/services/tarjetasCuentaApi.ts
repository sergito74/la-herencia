/**
 * Cuentas de tarjetas, control de integridad y cruces — 034-cuenta-corriente-tarjetas.
 * Ver specs/034-cuenta-corriente-tarjetas/contracts/tarjetas-cuenta-api.md.
 */

import { apiDelete, apiGet, apiPost, API_BASE_URL } from "@/services/apiClient";

export type OrigenFila = "Consumo" | "Cargo del resumen" | "Pago" | "Devolución";
export type EstadoVinculo = "vinculado" | "resto-con-proveedor" | "sin-proveedor" | "cruzado-con-devolucion";
export type AgruparCuenta = "movimientos" | "resumenes";

export interface ReferenciaFila {
  tipo: "linea-consumo" | "resumen" | "movimiento-bancario" | "cruce";
  idLineaConsumo?: number;
  idResumen?: number;
  medio?: string;
  idMovimiento?: number;
  idCruce?: number;
}

export interface TarjetaSaldo {
  idTarjeta: number;
  tarjeta: string;
  banco: string | null;
  activa: boolean;
  idContacto: number;
  deuda: number;
  credito: number;
  /** Criterio de la vista: crédito − deuda (negativo = se debe). */
  saldo: number;
  pendienteNeto: number;
  /** |saldo + pendienteNeto|; debe ser menor a $1 (FR-009). */
  diferenciaConModuloTarjetas: number | null;
  ultimoMovimiento: string | null;
  cuotasAVencer: number;
}

export interface ResumenTarjetasResponse {
  hasta: string;
  tarjetas: TarjetaSaldo[];
  total: { deuda: number; credito: number; saldo: number };
  tarjetasSinContacto: { idTarjeta: number; tarjeta: string; motivo: string }[];
  avisoSaldo: string;
}

export interface FilaCuenta {
  fecha: string | null;
  origen: OrigenFila;
  idResumen: number | null;
  codigo: string | null;
  detalle: string | null;
  proveedor: string | null;
  deuda: number;
  credito: number;
  saldo: number;
  estadoVinculo: EstadoVinculo | null;
  referencia: ReferenciaFila | null;
}

export interface CuotaAVencer {
  fechaVencimiento: string;
  importe: number;
  idCompra: number | null;
}

export interface CuentaTarjetaResponse {
  idTarjeta: number;
  tarjeta: string;
  idContacto: number;
  desde: string | null;
  hasta: string | null;
  saldoInicial: number;
  filas: FilaCuenta[];
  saldoFinal: number;
  /** exigible + noResumido = saldo de la cuenta (FR-023). */
  detalleSaldo: { exigible: number; noResumido: number };
  cuotasAVencer: CuotaAVencer[];
  apertura: { idContactoAnterior: number | null; contactoAnterior: string | null; informativo: boolean };
  avisoSaldo: string;
}

export function fetchResumenTarjetas(hasta?: string): Promise<ResumenTarjetasResponse> {
  return apiGet<ResumenTarjetasResponse>("/api/tarjetas-cuenta/resumen", { hasta });
}

export function fetchCuentaTarjeta(
  idTarjeta: number,
  filtros: { desde?: string; hasta?: string; agrupar?: AgruparCuenta } = {}
): Promise<CuentaTarjetaResponse> {
  return apiGet<CuentaTarjetaResponse>(`/api/tarjetas-cuenta/${idTarjeta}`, filtros);
}

export function urlExportarCuentaTarjeta(
  idTarjeta: number,
  filtros: { desde?: string; hasta?: string; agrupar?: AgruparCuenta } = {}
): string {
  const url = new URL(`/api/tarjetas-cuenta/${idTarjeta}/exportar`, API_BASE_URL);
  for (const [k, v] of Object.entries(filtros)) if (v) url.searchParams.set(k, v);
  return url.toString();
}

// ---- Control de integridad ------------------------------------------------

export type CategoriaControl =
  | "pago-en-proveedor"
  | "movimiento-sin-resumen"
  | "pago-sin-origen-o-importe"
  | "resumen-con-pendiente"
  | "devolucion-sin-cruzar"
  | "saldo-inicial-con-pagos"
  | "tarjeta-sin-contacto"
  | "consumo-sin-vinculo-con-deuda-abierta"
  | "consumo-sin-proveedor"
  | "diferencia-contrapartida"
  | "continuidad-de-resumenes"
  | "indicios-de-otra-moneda";

export interface HallazgoControl {
  categoria: CategoriaControl;
  idTarjeta: number | null;
  tarjeta: string | null;
  medio: string | null;
  idMovimiento: number | null;
  idResumen: number | null;
  idLineaConsumo: number | null;
  fecha: string | null;
  importe: number | null;
  motivo: string;
}

export interface ControlResponse {
  generado: string;
  resumenPorCategoria: Partial<Record<CategoriaControl, number>>;
  hallazgos: HallazgoControl[];
}

export function fetchControl(filtros: { idTarjeta?: number; categoria?: CategoriaControl } = {}): Promise<ControlResponse> {
  return apiGet<ControlResponse>("/api/tarjetas-cuenta/control", {
    idTarjeta: filtros.idTarjeta,
    categoria: filtros.categoria,
  });
}

export function urlExportarControl(filtros: { idTarjeta?: number; categoria?: CategoriaControl } = {}): string {
  const url = new URL("/api/tarjetas-cuenta/control/exportar", API_BASE_URL);
  if (filtros.idTarjeta) url.searchParams.set("idTarjeta", String(filtros.idTarjeta));
  if (filtros.categoria) url.searchParams.set("categoria", filtros.categoria);
  return url.toString();
}

// ---- Cruces -----------------------------------------------------------------

export type TipoCruce = "devolucion-debito" | "consumo-devolucion";

export interface MovimientoCruce {
  medio: string;
  idMovimiento: number;
  fecha: string | null;
  importe: number;
  concepto: string | null;
  idLineaConsumo?: number;
}

export interface SugerenciaCruce {
  tipo: TipoCruce;
  idTarjeta: number;
  origen: MovimientoCruce;
  destino?: MovimientoCruce;
  idLineaConsumo?: number;
  detalleLinea?: string | null;
  diasDiferencia: number;
  diferenciaImporte: number;
  puntaje: number;
}

export interface SugerenciasCruceResponse {
  sugerencias: SugerenciaCruce[];
}

export interface AltaCruce {
  tipo: TipoCruce;
  idTarjeta: number;
  sugerido: boolean;
  origen: { medio: string; idMovimiento: number };
  destino?: { medio: string; idMovimiento: number };
  idLineaConsumo?: number;
}

export interface Cruce {
  idCruce: number;
  tipo: TipoCruce;
  idTarjeta: number;
  importe: number;
  sugerido: boolean;
  usuario: string;
  fecha: string;
  medioOrigen?: string;
  idMovimientoOrigen?: number;
  medioDestino?: string | null;
  idMovimientoDestino?: number | null;
  idLineaConsumo?: number | null;
  deshecho: boolean;
  usuarioDeshecho: string | null;
  fechaDeshecho: string | null;
}

export function fetchSugerenciasCruce(
  filtros: { tipo: TipoCruce; idTarjeta?: number }
): Promise<SugerenciasCruceResponse> {
  return apiGet<SugerenciasCruceResponse>("/api/tarjetas-cuenta/cruces/sugerencias", {
    tipo: filtros.tipo,
    idTarjeta: filtros.idTarjeta,
  });
}

export function aprobarCruce(alta: AltaCruce): Promise<Cruce> {
  return apiPost<Cruce>("/api/tarjetas-cuenta/cruces", alta);
}

export function deshacerCruce(idCruce: number): Promise<void> {
  return apiDelete(`/api/tarjetas-cuenta/cruces/${idCruce}`);
}

export function fetchCruces(incluirDeshechos = false, idTarjeta?: number): Promise<Cruce[]> {
  return apiGet<Cruce[]>("/api/tarjetas-cuenta/cruces", {
    incluirDeshechos: incluirDeshechos ? "true" : undefined,
    idTarjeta,
  });
}
