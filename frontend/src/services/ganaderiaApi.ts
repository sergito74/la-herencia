import { apiGet, apiPost } from "@/services/apiClient";

export type VistaGanaderia = "ejercicio" | "campania";
export type MonedaGanaderia = "USD" | "ARS";

export interface FilaResultado {
  grupo: string;
  rubro: string;
  abreDetalle: boolean;
  valores: Record<string, number | null>;
}

export interface IndicadoresPeriodo {
  ventasNetas: number;
  ingresoNeto: number;
  margenBruto: number;
  estructura: number;
  resultadoOperativo: number;
  costoDirecto: number;
  haGanaderas: number;
  mbHa: number | null;
  costoDirectoHa: number | null;
  kgVendidos: number;
  cabezasVendidas: number;
  kgProducidos: number | null;
  costoPorKg: number | null;
  ev: number | null;
  evHa: number | null;
  sinInventario: boolean;
}

export interface ResultadoGanadero {
  vista: VistaGanaderia;
  moneda: MonedaGanaderia;
  conversion: string | null;
  periodos: { clave: string; desde: string; hasta: string; sinInventario: boolean }[];
  grupos: { grupo: string; titulo: string; signo: number }[];
  filas: FilaResultado[];
  indicadores: Record<string, IndicadoresPeriodo>;
  avisos: { periodo: string; texto: string }[];
  nota?: string | null;
}

export interface DetalleItem {
  fecha: string | null;
  documento: string | null;
  contacto: string | null;
  importe: number;
  enlace: string | null;
}

export const fetchResultadoGanadero = (vista: VistaGanaderia, moneda: MonedaGanaderia, desde: string, hasta: string,
  establecimiento?: number) =>
  apiGet<ResultadoGanadero>("/api/ganaderia/resultado", { vista, moneda, desde, hasta, establecimiento });

export const fetchDetalleGanadero = (grupo: string, rubro: string, periodo: string, vista: VistaGanaderia,
  establecimiento?: number) =>
  apiGet<{ items: DetalleItem[] }>("/api/ganaderia/resultado/detalle", { grupo, rubro, periodo, vista, establecimiento });

export const recalcularResultadoGanadero = () => apiPost<{ ok: boolean }>("/api/ganaderia/resultado/recalcular", {});
