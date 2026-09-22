/**
 * Resultado y Costos de Cultivo (012-resultado-costos-cultivo). Sus endpoints
 * son de solo lectura sobre `WC`, según FR-013 de esta spec.
 */

import { API_BASE_URL, apiGet } from "@/services/apiClient";

// ------------------------------------------------------------------ catálogo

export interface CampaniaItem {
  idCampania: number;
  campania: string;
}

export interface CatalogoCampanias {
  campanias: CampaniaItem[];
  campaniaActualId: number;
}

export const fetchCampanias = () => apiGet<CatalogoCampanias>("/api/resultado-cultivo/campanias");

// ------------------------------------------------------------------ resultado

export interface ResultadoCultivoResumen {
  idCultivo: number;
  cultivo: string;
  superficieSembrada: number;
  costoTotalPesos: number;
  costoTotalDolares: number;
  costeoDolaresIncompleto: boolean;
  ventaNetaPesos: number;
  ventaNetaDolares: number;
  margenBrutoPesos: number;
  margenBrutoDolares: number;
  rentabilidadPesos: number | null;
  rentabilidadDolares: number | null;
  supCosechaEstimada: boolean;
  advertenciaMargenNoRepresentativo: boolean;
}

export interface CostoSinClasificar {
  montoPesos: number;
  montoDolares: number;
  motivo: string;
}

export interface ResultadoCampania {
  idCampania: number;
  campania: string;
  superficieSembrada: number;
  superficieCosechada: number | null;
  superficieCosechadaCompleta: boolean;
  superficiePicada: number | null;
  costoTotalPesos: number;
  costoTotalDolares: number;
  costeoDolaresIncompleto: boolean;
  costoPorHectareaSembradaPesos: number | null;
  costoPorHectareaSembradaDolares: number | null;
  costoPorHectareaCosechadaPesos: number | null;
  costoPorHectareaCosechadaDolares: number | null;
  ventaNetaPesos: number;
  ventaNetaDolares: number;
  margenBrutoPesos: number;
  margenBrutoDolares: number;
  rentabilidadPesos: number | null;
  rentabilidadDolares: number | null;
  cultivos: ResultadoCultivoResumen[];
  costoSinClasificar: CostoSinClasificar | null;
}

export const fetchResultadoCampania = (idCampania: number) => apiGet<ResultadoCampania>(`/api/resultado-cultivo/campania/${idCampania}`);

export interface ResultadoCultivo {
  idCultivo: number;
  cultivo: string;
  idCampania: number;
  campania: string;
  superficieSembrada: number;
  superficieCosechada: number | null;
  superficiePicada: number | null;
  rinde: number | null;
  costoTotalPesos: number;
  costoTotalDolares: number;
  costeoDolaresIncompleto: boolean;
  costoPorHectareaSembradaPesos: number | null;
  costoPorHectareaSembradaDolares: number | null;
  costoPorHectareaCosechadaPesos: number | null;
  costoPorHectareaCosechadaDolares: number | null;
  ventaNetaPesos: number;
  ventaNetaDolares: number;
  margenBrutoPesos: number;
  margenBrutoDolares: number;
  rentabilidadPesos: number | null;
  rentabilidadDolares: number | null;
  supCosechaEstimada: boolean;
  advertenciaMargenNoRepresentativo: boolean;
}

export const fetchResultadoCultivo = (idCampania: number, idCultivo: number) =>
  apiGet<ResultadoCultivo>(`/api/resultado-cultivo/campania/${idCampania}/cultivo/${idCultivo}`);

// ------------------------------------------------------------------ detalle de costos

export type OrigenCosto = "Compra" | "OrdenTrabajo" | "Seguro" | "MaquinariaPropia";

export interface DetalleCostoItem {
  concepto: string;
  rubro: string | null;
  montoPesos: number;
  montoDolares: number | null;
  origen: OrigenCosto;
  idCompra: number | null;
  idDetalleCompra: number | null;
  idOrdenTrabajo: number | null;
}

export const fetchDetalleCostos = (idCampania: number, idCultivo: number) =>
  apiGet<DetalleCostoItem[]>(`/api/resultado-cultivo/campania/${idCampania}/cultivo/${idCultivo}/costos`);

// ------------------------------------------------------------------ exportación

export const urlExportarCampania = (idCampania: number) => new URL(`/api/resultado-cultivo/campania/${idCampania}/exportar`, API_BASE_URL).toString();

export const urlExportarCultivo = (idCampania: number, idCultivo: number) =>
  new URL(`/api/resultado-cultivo/campania/${idCampania}/cultivo/${idCultivo}/exportar`, API_BASE_URL).toString();
