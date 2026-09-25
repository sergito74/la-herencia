import { apiGet } from "@/services/apiClient";

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
