import { API_BASE_URL, apiGet } from "@/services/apiClient";

export interface CuentaResumen {
  banco: string;
  numeroCuenta: string;
  ingresos: number;
  egresos: number;
  neto: number;
}

export interface MovimientosInternos {
  ingresos: number;
  egresos: number;
  total: number;
}

export interface SinClasificar {
  cantidad: number;
  importeAbsoluto: number;
}

export interface PeriodoResumen {
  periodo: string;
  porCuenta: CuentaResumen[];
  totalIngresos: number;
  totalEgresos: number;
  totalNeto: number;
  movimientosInternos: MovimientosInternos;
  sinClasificar: SinClasificar;
}

export interface UltimaCarga {
  banco: string;
  numeroCuenta: string;
  fecha: string | null;
}

export interface ResumenFlujoCaja {
  periodos: PeriodoResumen[];
  ultimaCarga: UltimaCarga[];
}

export interface MovimientoFlujoCaja {
  fecha: string;
  banco: string;
  origenMovimiento: string | null;
  idMovimientoOrigen: number | null;
  numeroCuentaBancaria: string | null;
  concepto: string | null;
  importe: number;
  idContacto: number | null;
  contacto: string | null;
  esInterno: boolean;
}

export type Granularidad = "mensual" | "semanal";

export function fetchResumen(params: {
  fechaDesde?: string;
  fechaHasta?: string;
  granularidad?: Granularidad;
}): Promise<ResumenFlujoCaja> {
  return apiGet<ResumenFlujoCaja>("/api/flujo-caja/resumen", params);
}

export function fetchDetalle(params: {
  fechaDesde: string;
  fechaHasta: string;
  banco?: string;
  numeroCuenta?: string;
  soloInternos?: boolean;
}): Promise<{ movimientos: MovimientoFlujoCaja[] }> {
  return apiGet<{ movimientos: MovimientoFlujoCaja[] }>("/api/flujo-caja/detalle", {
    ...params,
    soloInternos: params.soloInternos ? "true" : undefined,
  });
}

// --- 030: Flujo de caja por rubro (contracts/api.md) ---

export type GranularidadRubro = "semanal" | "mensual" | "trimestral" | "anual";
export type MonedaRubro = "ARS" | "USD";
export type SeccionRubro = "ingresos" | "egresos" | "internos";

export interface FilaRubro {
  rubro: string;
  valores: Record<string, number>;
  total: number;
}

export interface GrupoCentroCosto {
  centroCosto: string;
  rubros: FilaRubro[];
  subtotalPorPeriodo: Record<string, number>;
  subtotal: number;
}

export interface FlujoPorRubro {
  moneda: MonedaRubro;
  periodos: string[];
  saldoInicial: { cuentas: { cuenta: string; importe: number | null; aclaracion?: string | null }[]; total: number | null };
  ingresos: { rubros: FilaRubro[]; totalPorPeriodo: Record<string, number> };
  egresos: { centrosCosto: GrupoCentroCosto[]; totalPorPeriodo: Record<string, number> };
  netoOperativoPorPeriodo: Record<string, number>;
  internos: { rubros: FilaRubro[]; totalPorPeriodo: Record<string, number> };
  saldoFinalPorPeriodo: Record<string, number | null>;
  saldoFinalPorCuenta: Record<string, Record<string, number | null>>;
  sinTipoCambio: { periodo: string; seccion: SeccionRubro; centroCosto: string | null; rubro: string; cantidad: number; importeArs: number }[];
  saldosSinTipoCambio: string[];
  traspasosSinContraparte: { fecha: string; cuenta: string; importe: number; idMovimiento: number | null }[];
  ultimaFechaCotizacion: string | null;
}

export interface ParteMovimiento {
  fecha: string;
  cuenta: string;
  concepto: string | null;
  contacto: string | null;
  seccion: SeccionRubro;
  rubro: string;
  centroCosto: string | null;
  importeArs: number;
  importeMovimiento: number;
  documentoAplicado: { tipo: string; id: number; via: string } | null;
  cotizacion: number | null;
  fechaCotizacion: string | null;
  importeUsd: number | null;
  origenMovimiento: string | null;
  idMovimiento: number | null;
}

export interface ParamsPorRubro {
  fechaDesde: string;
  fechaHasta: string;
  granularidad: GranularidadRubro;
  moneda: MonedaRubro;
}

export function fetchPorRubro(p: ParamsPorRubro): Promise<FlujoPorRubro> {
  return apiGet<FlujoPorRubro>("/api/flujo-caja/por-rubro", { ...p });
}

export function fetchDetalleRubro(
  p: ParamsPorRubro & { periodo: string; seccion: SeccionRubro; rubro: string; centroCosto?: string | null }
): Promise<{ total: number; items: ParteMovimiento[] }> {
  const { centroCosto, ...resto } = p;
  return apiGet("/api/flujo-caja/por-rubro/detalle", { ...resto, ...(centroCosto ? { centroCosto } : {}) });
}

export function urlExportarPorRubro(p: ParamsPorRubro): string {
  const url = new URL("/api/flujo-caja/por-rubro/exportar", API_BASE_URL);
  Object.entries(p).forEach(([k, v]) => url.searchParams.set(k, v));
  return url.toString();
}
