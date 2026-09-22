/**
 * Órdenes de Trabajo (011-ordenes-trabajo). Escribe exclusivamente contra `WC`.
 */

import { API_BASE_URL, apiGet, apiPatch, apiPost } from "@/services/apiClient";
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
}

export interface FiltrosOrdenes {
  idContratista?: number | null;
  idLote?: number | null;
  idCultivo?: number | null;
  idCampania?: number | null;
  fechaDesde?: string;
  fechaHasta?: string;
  estado?: string;
}

export const fetchOrdenes = (f: FiltrosOrdenes, page: number, pageSize = 25) =>
  apiGet<Paginado<OrdenListItem>>("/api/ordenes", {
    idContratista: f.idContratista ?? undefined,
    idLote: f.idLote ?? undefined,
    idCultivo: f.idCultivo ?? undefined,
    idCampania: f.idCampania ?? undefined,
    fechaDesde: f.fechaDesde,
    fechaHasta: f.fechaHasta,
    estado: f.estado,
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
  cantidadTotal: number;
  unidad: string;
  distribuciones: DistribucionDetalle[];
  devoluciones: DevolucionDetalle[];
}

export interface FormularioRetiro {
  idFormularioRetiro: number;
  fechaEmision: string;
}

export interface OrdenDetalle extends OrdenListItem {
  motivoAnulacion: string | null;
  observaciones: string | null;
  insumos: RenglonInsumoDetalle[];
  maquinaria: { idOrdenMaquinaria: number; descripcion: string; costoPorHectarea: number; tipoCambioBna: number | null }[];
  facturaContratista: { idCompra: number; tipoDocumento: string; numeroDocumento: string; moneda: string; tipoDeCambio: number | null } | null;
  formularioRetiro: FormularioRetiro | null;
  tieneDevoluciones: boolean;
  editable: boolean;
}

export const fetchOrden = (id: number) => apiGet<OrdenDetalle>(`/api/ordenes/${id}`);

export const crearOrden = (datos: OrdenIn) => apiPost<{ idOrden: number; idFormularioRetiro: number }>("/api/ordenes", datos);

export const editarOrden = (id: number, datos: OrdenIn) => apiPatch<{ idOrden: number }>(`/api/ordenes/${id}`, datos);

export const ejecutarOrden = (id: number, fechaEjecucion: string) => apiPost<void>(`/api/ordenes/${id}/ejecutar`, { fechaEjecucion });

export const anularOrden = (id: number, motivo: string) => apiPost<void>(`/api/ordenes/${id}/anular`, { motivo });

export const ejecutarOrdenUrlExportar = (f: FiltrosOrdenes) => {
  const url = new URL("/api/ordenes/exportar", API_BASE_URL);
  Object.entries(f).forEach(([k, v]) => v != null && v !== "" && url.searchParams.set(k, String(v)));
  return url.toString();
};

export const urlExportarFormularioRetiro = (idOrden: number) => new URL(`/api/ordenes/${idOrden}/formulario-retiro/exportar`, API_BASE_URL).toString();

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

// ------------------------------------------------------------------ factura de contratista (Historia 4)

export const vincularFacturaContratista = (idOrden: number, idCompra: number) =>
  apiPost<{ montoPesos: number; montoDolares: number | null; porLote: Record<number, number> }>(`/api/ordenes/${idOrden}/factura`, { idCompra });

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
