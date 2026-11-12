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
  valuacionDolaresIncompleta?: boolean;
  montoPesos: number;
  montoDolares: number;
  motivo: string;
}

export interface ResultadoCampania {
  /** 039: ingresos fuera de cultivos (pastaje), netos de IVA; no forman parte del margen de cultivos. */
  otrosIngresos?: { concepto: string; establecimiento: string; netoPesos: number }[];
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

/* ---- Formularios de Access (FrmCostos / FrmResultados), 12/11/2026 ---- */

export interface ParMonto { pesos: number; dolares: number; haPesos?: number; haDolares?: number }
export interface CostoDirecto { idRubro: number; concepto: string; pesos: number; dolares: number; haPesos: number; haDolares: number }

export interface FormularioCostos {
  cultivo: string; campania: string; sinSuperficie: boolean; fechaInicio?: string | null;
  superficieAfectada?: number; superficieSembrada?: number; superficieSembradaTeorica?: boolean; superficiePicada?: number;
  costosDirectos?: CostoDirecto[]; implantacion?: ParMonto; silo?: ParMonto; total?: ParMonto;
}

export interface DetalleRubroItem {
  cantidad: number; producto: string; unitarioPesos: number | null; unitarioDolares: number | null; totalPesos: number; totalDolares: number;
}

export interface FormularioResultados {
  cultivo: string; campania: string; aviso: string | null;
  fechaInicio?: string; fechaFin?: string | null; ocupacionDias?: number | null;
  superficieAfectada?: number; superficieSembrada?: number; superficieSembradaTeorica?: boolean; superficieCosechada?: number; superficiePicada?: number;
  cantidadCosechada?: number; cantidadVendida?: number; cantidadConsumida?: number;
  rinde?: number; rindeIndiferencia?: number; volumenIndiferencia?: number;
  margenBruto?: ParMonto; margenBrutoHa?: ParMonto; rentabilidad?: ParMonto; rentaAnual?: ParMonto; precioNetoTn?: number;
  costosDirectos?: CostoDirecto[]; implantacion?: ParMonto; silo?: ParMonto; cosecha?: ParMonto; totalCostos?: ParMonto;
  ventaBruta?: ParMonto; bonificaciones?: ParMonto; totalVentas?: ParMonto;
  deducciones?: { detalle: string; pesos: number; dolares: number }[];
  gastos?: { concepto: string; pesos: number; dolares: number }[];
  totalDeducciones?: ParMonto; recuperoSeguro?: ParMonto; produccionNoComercializada?: ParMonto; totalVentaNeta?: ParMonto;
}

export const fetchCampaniasDeCultivo = (idCultivo: number) =>
  apiGet<CampaniaItem[]>(`/api/resultado-cultivo/access/cultivo/${idCultivo}/campanias`);
export const fetchFormularioCostos = (idCultivo: number, idCampania: number) =>
  apiGet<FormularioCostos>(`/api/resultado-cultivo/access/costos?idCultivo=${idCultivo}&idCampania=${idCampania}`);
export const fetchDetalleRubro = (idCultivo: number, idCampania: number, idRubro: number) =>
  apiGet<DetalleRubroItem[]>(`/api/resultado-cultivo/access/costos/detalle?idCultivo=${idCultivo}&idCampania=${idCampania}&idRubro=${idRubro}`);
export const fetchFormularioResultados = (idCultivo: number, idCampania: number) =>
  apiGet<FormularioResultados>(`/api/resultado-cultivo/access/resultados?idCultivo=${idCultivo}&idCampania=${idCampania}`);
