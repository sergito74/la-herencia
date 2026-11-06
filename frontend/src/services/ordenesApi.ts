/**
 * Órdenes de Trabajo (011-ordenes-trabajo). Escribe exclusivamente contra `WC`.
 */

import { API_BASE_URL, apiDelete, apiGet, apiPatch, apiPost } from "@/services/apiClient";
import type { Paginado } from "@/services/remitosApi";

// ------------------------------------------------------------------ catálogos

export interface Lote {
  idLote: number;
  numeroLote: string;
  superficie: number;
}

export interface Cultivo {
  idCultivo: number;
  nombre: string;
}

export interface Campania {
  idCampania: number;
  nombre: string;
}

export interface TipoLabor {
  idTipoLabor: number;
  nombre: string;
}

export interface Contratista {
  idContratistaContacto: number;
  nombre: string;
}

export interface PlanAgricolaItem {
  idPlanAgricola: number;
  idLote: number;
  numeroLote: string | null;
  superficie: number | null;
  idCultivo: number;
  cultivo: string | null;
  idCampania: number;
  campania: string | null;
}

export interface CatalogosOrdenes {
  lotes: Lote[];
  cultivos: Cultivo[];
  campanias: Campania[];
  tiposLabor: TipoLabor[];
  contratistas: Contratista[];
  planAgricola: PlanAgricolaItem[];
}

export const fetchCatalogosOrdenes = () => apiGet<CatalogosOrdenes>("/api/ordenes/catalogos");

// ------------------------------------------------------------------ órdenes

export type EstadoOrden = "Planificada" | "Ejecutada" | "Anulada";

export interface DistribucionIn {
  idLote: number;
  idCultivo: number;
  idCampania: number;
  dosisHa: number;
  superficie: number;
  aplicar: boolean;
}

export interface RenglonInsumoIn {
  idProducto: number;
  unidad: string;
  cantidadTotal: number;
  distribuciones: DistribucionIn[];
}

export interface OrdenIn {
  fecha: string;
  idTipoLabor: number;
  idContratistaContacto?: number | null;
  renglones: RenglonInsumoIn[];
  idRubro?: number | null;
  idCentroCostos?: number | null;
  observaciones?: string | null;
  confirmar?: boolean;
}

export interface OrdenListItem {
  idOrden: number;
  fechaPedido: string | null;
  fechaEjecucion: string | null;
  idTipoLabor: number;
  tipoLabor: string | null;
  idContratistaContacto: number | null;
  contratista: string | null;
  estado: EstadoOrden;
  idRubro: number | null;
  idCentroCostos: number | null;
  /** Solo al filtrar por insumo: los insumos de la orden que coinciden, con lo usado. */
  insumosCoincidentes?: { producto: string; cantidad: number; unidad: string }[];
}

export interface FiltrosOrdenes {
  idContratista?: number | null;
  idTipoLabor?: number | null;
  idLote?: number | null;
  idCultivo?: number | null;
  idCampania?: number | null;
  fechaDesde?: string;
  fechaHasta?: string;
  estado?: string;
  /** Nombre comercial o principio activo de un insumo usado en la orden. */
  insumo?: string;
}

export const fetchOrdenes = (f: FiltrosOrdenes, page: number, pageSize = 25) =>
  apiGet<Paginado<OrdenListItem>>("/api/ordenes", {
    idContratista: f.idContratista ?? undefined,
    idTipoLabor: f.idTipoLabor ?? undefined,
    idLote: f.idLote ?? undefined,
    idCultivo: f.idCultivo ?? undefined,
    idCampania: f.idCampania ?? undefined,
    fechaDesde: f.fechaDesde,
    fechaHasta: f.fechaHasta,
    estado: f.estado,
    insumo: f.insumo || undefined,
    page,
    pageSize,
  });

export interface DistribucionDetalle extends DistribucionIn {
  idDistrib: number;
  lote: string | null;
  cultivo: string | null;
  campania: string | null;
  cantidadAsignada: number;
}

export interface DevolucionDetalle {
  idDevolucion: number;
  fecha: string;
  cantidad: number;
  observaciones: string | null;
}

export interface RenglonInsumoDetalle {
  idOrdenInsumo: number;
  idProducto: number;
  producto: string | null;
  ingredienteActivo: string | null;
  cantidadTotal: number;
  /** Ajustes por recuento físico repartidos a este renglón: consumo efectivo = cantidadTotal + ajusteRecuento. */
  ajusteRecuento: number;
  unidad: string;
  distribuciones: DistribucionDetalle[];
  devoluciones: DevolucionDetalle[];
}

export interface FormularioRetiro {
  idFormularioRetiro: number;
  fechaEmision: string;
}

/** 048: documento del contratista vinculado (solo lectura) y lo imputado a esta orden. */
export interface DocumentoContratista {
  idCompra: number;
  tipoDocumento: string;
  numeroDocumento: string;
  fecha: string;
  moneda: string;
  tipoDeCambio: number | null;
  neto: number;
  reparto: { idOrden: number | null; lote: string | null; cultivo: string | null; campania: string | null; importe: number }[];
}

export interface OrdenDetalle extends OrdenListItem {
  motivoAnulacion: string | null;
  observaciones: string | null;
  insumos: RenglonInsumoDetalle[];
  maquinaria: { idOrdenMaquinaria: number; descripcion: string; costoPorHectarea: number; tipoCambioBna: number | null }[];
  facturasContratista: (DocumentoContratista & { notasRelacionadas: DocumentoContratista[] })[];
  formularioRetiro: FormularioRetiro | null;
  tieneDevoluciones: boolean;
  editable: boolean;
}

export const fetchOrden = (id: number) => apiGet<OrdenDetalle>(`/api/ordenes/${id}`);

export const crearOrden = (datos: OrdenIn) => apiPost<{ idOrden: number; idFormularioRetiro: number }>("/api/ordenes", datos);

export const editarOrden = (id: number, datos: OrdenIn) => apiPatch<{ idOrden: number }>(`/api/ordenes/${id}`, datos);

export const ejecutarOrden = (id: number, fechaEjecucion: string) => apiPost<void>(`/api/ordenes/${id}/ejecutar`, { fechaEjecucion });

export const corregirFechaEjecucion = (id: number, fechaEjecucion: string) => apiPatch<void>(`/api/ordenes/${id}/fecha-ejecucion`, { fechaEjecucion });

export const anularOrden = (id: number, motivo: string) => apiPost<void>(`/api/ordenes/${id}/anular`, { motivo });

export const ejecutarOrdenUrlExportar = (f: FiltrosOrdenes) => {
  const url = new URL("/api/ordenes/exportar", API_BASE_URL);
  Object.entries(f).forEach(([k, v]) => v != null && v !== "" && url.searchParams.set(k, String(v)));
  return url.toString();
};

export const urlExportarFormularioRetiro = (idOrden: number) => new URL(`/api/ordenes/${idOrden}/formulario-retiro/exportar`, API_BASE_URL).toString();
export const urlPdfFormularioRetiro = (idOrden: number) => new URL(`/api/ordenes/${idOrden}/formulario-retiro/pdf`, API_BASE_URL).toString();

// ------------------------------------------------------------------ devoluciones (Historia 2)

export const registrarDevolucion = (idOrden: number, idOrdenInsumo: number, datos: { fecha: string; cantidad: number; observaciones?: string | null }) =>
  apiPost<{ idDevolucion: number }>(`/api/ordenes/${idOrden}/insumos/${idOrdenInsumo}/devoluciones`, datos);

// ------------------------------------------------------------------ maquinaria propia (Historia 3)

export interface MaquinariaIn {
  descripcion: string;
  costoPorHectarea: number;
  tipoCambioBna?: number | null;
}

export const agregarMaquinaria = (idOrden: number, datos: MaquinariaIn) =>
  apiPost<{ idOrdenMaquinaria: number; montoTotal: number; porLote: Record<number, number> }>(`/api/ordenes/${idOrden}/maquinaria`, datos);

// 048: la factura del contratista se vincula desde Compras (panel "Órdenes de trabajo").

// ------------------------------------------------------------------ resultado por cultivo/campaña (Historia 6)

export interface CostoCultivoCampania {
  idCultivo: number;
  cultivo: string | null;
  idCampania: number;
  campania: string | null;
  idLote: number;
  lote: string | null;
  costoInsumos: number;
  costoMaquinaria: number;
  costoContratista: number;
  costoTotalOrdenes: number;
}

export interface ResumenCampaniaHeredado {
  idCampania: number;
  campania: string | null;
  totalCostoPesos: number | null;
  totalCostoDolares: number | null;
  margenBrutoPesos: number | null;
}

export interface ResultadoCultivo {
  porCultivoCampania: CostoCultivoCampania[];
  resumenCampaniaHeredado: ResumenCampaniaHeredado[];
}

export const fetchResultadoCultivo = (f: { idCultivo?: number | null; idCampania?: number | null; idLote?: number | null }) =>
  apiGet<ResultadoCultivo>("/api/ordenes/resultado-cultivo", {
    idCultivo: f.idCultivo ?? undefined,
    idCampania: f.idCampania ?? undefined,
    idLote: f.idLote ?? undefined,
  });

export const urlExportarResultadoCultivo = (f: { idCultivo?: number | null; idCampania?: number | null; idLote?: number | null }) => {
  const url = new URL("/api/ordenes/resultado-cultivo/exportar", API_BASE_URL);
  if (f.idCultivo) url.searchParams.set("idCultivo", String(f.idCultivo));
  if (f.idCampania) url.searchParams.set("idCampania", String(f.idCampania));
  if (f.idLote) url.searchParams.set("idLote", String(f.idLote));
  return url.toString();
};

// ------------------------------------------------------------------ catálogo de labores (Historia 7)

export const fetchTiposLabor = () => apiGet<TipoLabor[]>("/api/ordenes/tipos-labor");

export const crearTipoLabor = (nombre: string) => apiPost<{ idTipoLabor: number }>("/api/ordenes/tipos-labor", { nombre });

// ------------------------------------------------------------------ hectáreas aplicadas (04/11/2026)

export interface RepartoCultivo {
  cultivo: string | null;
  producto: string | null;
  unidad: string | null;
  cantidad: number;
}

export const corregirHectareas = (idOrden: number, lotes: { idLote: number; superficie: number }[]) =>
  apiPatch<{ repartoPorCultivo: RepartoCultivo[] }>(`/api/ordenes/${idOrden}/hectareas`, { lotes });

export const fetchRepartoCultivos = (idOrden: number) =>
  apiGet<{ repartoPorCultivo: RepartoCultivo[] }>(`/api/ordenes/${idOrden}/reparto-cultivos`);

// --- 048: facturas de labor de contratistas sin orden de trabajo ---------------------------------------------

export interface RenglonSinOrden {
  idCompra: number;
  contratista: string;
  fecha: string;
  numero: string;
  moneda: string;
  rubro: string | null;
  concepto: string | null;
  cantidad: number | null;
  unidad: string | null;
  neto: number;
  destino: string | null;
  campania: string | null;
}

export const fetchFacturasSinOrden = () => apiGet<RenglonSinOrden[]>("/api/ordenes/contratistas/sin-orden");
export const urlExportarFacturasSinOrden = () => new URL("/api/ordenes/contratistas/sin-orden/exportar", API_BASE_URL).toString();
