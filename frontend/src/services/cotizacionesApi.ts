import { apiGet, apiPost } from "./apiClient";

export interface CotizacionDia {
  fecha: string;
  inmag: number | null;
  cabezasIngresadas: number | null;
  inmagOrigen: string | null;
  dolarCompraBillete: number | null;
  dolarVentaBillete: number | null;
  dolarPromedioBillete: number | null;
  dolarCompraDivisa: number | null;
  dolarVentaDivisa: number | null;
}

export interface ActualizarCotizacionesRespuesta {
  status: string;
  inmag_agregados: number;
  dolar_agregados: number;
  mensaje: string;
}

export function fetchCotizaciones(params: { mes?: string; desde?: string; hasta?: string }): Promise<CotizacionDia[]> {
  return apiGet<CotizacionDia[]>("/api/finanzas/cotizaciones", params as Record<string, string>);
}

export function actualizarCotizaciones(): Promise<ActualizarCotizacionesRespuesta> {
  return apiPost<ActualizarCotizacionesRespuesta>("/api/finanzas/cotizaciones/actualizar", {});
}

