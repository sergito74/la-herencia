/**
 * Remitos y stock de insumos (010-remitos). Escribe exclusivamente contra `WC`.
 */

import { API_BASE_URL, apiDelete, apiGet, apiPost, apiPut } from "@/services/apiClient";

// ------------------------------------------------------------------ catálogo

export interface Unidad {
  codigo: string;
  nombre: string;
  magnitud: string | null;
  esBase: boolean;
}

export interface Producto {
  idProducto: number;
  producto: string;
  tipo: string | null;
  ingredienteActivo: string | null;
  unidadBase: string | null;
  unidadConfirmada: boolean | null;
  unidadOrigen: string | null;
  equivalencias?: { unidad: string; factor: number }[];
  unidadBaseSugerida?: string;
}

export interface ProductoPorConfirmar {
  idProducto: number;
  producto: string;
  tipo: string | null;
  unidadBase: string;
  origen: string | null;
  renglones: number;
}

export const fetchUnidades = () => apiGet<Unidad[]>("/api/stock/unidades");
export const buscarProductos = (q: string, tipo?: string) => apiGet<Producto[]>("/api/stock/productos", { q, tipo, limite: 30 });
export const fetchProducto = (id: number) => apiGet<Producto>(`/api/stock/productos/${id}`);
export const fetchTiposProducto = () => apiGet<string[]>("/api/stock/productos/tipos");
export const fetchProductosPorConfirmar = () => apiGet<ProductoPorConfirmar[]>("/api/stock/productos/por-confirmar");
export const confirmarUnidades = (ids: number[]) => apiPost<{ confirmadas: number }>("/api/stock/productos/confirmar-unidades", { ids });
export const setUnidadBase = (id: number, unidad: string) => apiPut<void>(`/api/stock/productos/${id}/unidad-base`, { unidad });
export const setEquivalencia = (id: number, unidad: string, factor: number) =>
  apiPut<void>(`/api/stock/productos/${id}/equivalencias`, { unidad, factor });

// ------------------------------------------------------------------ remitos

export type EstadoFactura = "SinFactura" | "Facturado";
export type EstadoRenglones = "SinVincular" | "Parcial" | "Completo" | "ConDiferencia";

export interface RemitoListItem {
  idRemito: number;
  fecha: string | null;
  idProveedor: number;
  proveedor: string | null;
  nroRemito: string | null;
  idEstablecimiento: number | null;
  anulado: boolean;
  revisarDuplicado: boolean;
  archivo: string | null;
  renglones: number;
  productos: string;
  facturas: string[];
  estadoFactura: EstadoFactura;
  estadoRenglones: EstadoRenglones;
  diasSinFactura: number | null;
}

export interface Paginado<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface FiltrosRemitos {
  idProveedor?: number | null;
  producto?: string;
  nroRemito?: string;
  fechaDesde?: string;
  fechaHasta?: string;
  estado?: string;
}

export const fetchRemitos = (f: FiltrosRemitos, page: number, pageSize = 25) =>
  apiGet<Paginado<RemitoListItem>>("/api/remitos", {
    idProveedor: f.idProveedor ?? undefined,
    producto: f.producto,
    nroRemito: f.nroRemito,
    fechaDesde: f.fechaDesde,
    fechaHasta: f.fechaHasta,
    estado: f.estado,
    page,
    pageSize,
  });

export interface VinculoRenglon {
  idVinculo: number;
  idDetalle: number;
  idDetalleCompra: number;
  idCompra: number;
  descripcion: string | null;
  cantidad: number;
  cantidadCompra: number;
  precioUnitario: number;
  tipoDocumento: string | null;
  numeroDocumento: string | null;
  fechaCompra: string | null;
  moneda: string | null;
}

export interface RenglonRemito {
  idDetalle: number;
  idProducto: number;
  producto: string | null;
  tipo: string | null;
  cantidad: number;
  unidad: string;
  vencimiento: string | null;
  unidadBase: string | null;
  factorABase: number;
  equivalenciaPendiente: boolean;
  vinculos: VinculoRenglon[];
  cantidadVinculada: number;
  estadoVinculo: EstadoRenglones;
  costoUnitario: number | null;
  consumido: number;
  congelado: boolean;
  motivoCongelado: "consumo" | "factura" | null;
}

export interface RemitoDetalle {
  idRemito: number;
  fecha: string | null;
  idProveedor: number;
  proveedor: string | null;
  nroRemito: string | null;
  nroFacturaTexto: string | null;
  idEstablecimiento: number | null;
  observaciones: string | null;
  archivo: string | null;
  anulado: boolean;
  motivoAnulacion: string | null;
  revisarDuplicado: boolean;
  renglones: RenglonRemito[];
  facturas: { idCompra: number; tipoDocumento: string | null; numeroDocumento: string | null; fecha: string | null; moneda: string | null }[];
  estadoFactura: EstadoFactura;
  estadoRenglones: EstadoRenglones;
  congelado: boolean;
}

export interface RenglonInput {
  idDetalle?: number | null;
  idProducto: number;
  cantidad: number;
  unidad: string;
  vencimiento?: string | null;
  unidadBase?: string | null;
  factorUnidad?: number | null;
}

export interface RemitoInput {
  fecha: string;
  idProveedor: number;
  nroRemito: string;
  idEstablecimiento?: number | null;
  observaciones?: string | null;
  archivo?: string | null;
  renglones: RenglonInput[];
  confirmar?: boolean;
}

export const fetchRemito = (id: number) => apiGet<RemitoDetalle>(`/api/remitos/${id}`);
export const crearRemito = (input: RemitoInput) => apiPost<{ idRemito: number }>("/api/remitos", input);
export const actualizarRemito = (id: number, input: RemitoInput) => apiPut<{ idRemito: number }>(`/api/remitos/${id}`, input);
export const anularRemito = (id: number, motivo: string) => apiPost<void>(`/api/remitos/${id}/anular`, { motivo });
export const validarRemito = (idProveedor: number, nroRemito: string, idExcluir?: number) =>
  apiPost<{ formato: boolean; duplicados: { idRemito: number; fecha: string | null }[]; mensajes: string[] }>("/api/remitos/validar", {
    idProveedor,
    nroRemito,
    idExcluir: idExcluir ?? null,
  });
export const fetchCatalogosRemitos = () => apiGet<{ establecimientos: { id: number; nombre: string }[] }>("/api/remitos/catalogos");

export interface LineaFactura {
  idCompra: number;
  idDetalleCompra: number;
  idProducto: number | null;
  productoAsignado: boolean;
  descripcion: string | null;
  cantidad: number;
  precioUnitario: number;
  remitida: number;
  pendiente: number;
}

export interface FacturaCandidata {
  idCompra: number;
  tipoDocumento: string | null;
  numeroDocumento: string | null;
  fecha: string | null;
  moneda: string | null;
  vinculada: boolean;
  lineas: LineaFactura[];
}

export const fetchFacturasCandidatas = (idRemito: number) => apiGet<FacturaCandidata[]>(`/api/remitos/${idRemito}/facturas-candidatas`);
export const vincularRenglones = (idRemito: number, items: { idDetalleRemito: number; idDetalleCompra: number; cantidad: number }[]) =>
  apiPost<{ advertencias: string[] }>(`/api/remitos/${idRemito}/vinculos`, { items });
export const desvincularRenglon = (idRemito: number, idVinculo: number) => apiDelete(`/api/remitos/${idRemito}/vinculos/${idVinculo}`);
export const vincularFactura = (idRemito: number, idCompra: number) => apiPost<void>(`/api/remitos/${idRemito}/facturas`, { idCompra });
export const desvincularFactura = (idRemito: number, idCompra: number) => apiDelete(`/api/remitos/${idRemito}/facturas/${idCompra}`);

export interface FacturaSinRemito {
  idCompra: number;
  fecha: string | null;
  tipoDocumento: string | null;
  numeroDocumento: string | null;
  proveedor: string | null;
  idProveedor: number;
  moneda: string | null;
  renglones: number;
  neto: number;
}

export const fetchFacturasSinRemito = (f: { fechaDesde?: string; fechaHasta?: string; proveedor?: string }, page: number, pageSize = 25) =>
  apiGet<Paginado<FacturaSinRemito>>("/api/remitos/facturas-sin-remito", { ...f, page, pageSize });

// ------------------------------------------------------------------ stock

export interface Existencia {
  idProducto: number;
  producto: string;
  tipo: string | null;
  unidadBase: string | null;
  existencia: number;
  valor: number;
  costoPromedio: number | null;
  cantidadCostoPendiente: number;
  negativo: boolean;
  equivalenciaPendiente: boolean;
  sinUnidadBase: boolean;
}

export interface ExistenciasResponse {
  items: Existencia[];
  totales: { productos: number; valor: number; conCostoPendiente: number; negativos: number };
}

export interface MovimientoKardex {
  fecha: string | null;
  clave: string;
  tipo: string;
  detalle: string;
  idRemito?: number | null;
  cantidad: number;
  costoUnitario: number | null;
  importe: number | null;
  costoPendiente: boolean;
  sinCobertura?: number;
  restante?: number;
  saldo: number;
}

export interface Kardex {
  producto: { idProducto: number; producto: string; tipo: string | null };
  unidadBase: string | null;
  movimientos: MovimientoKardex[];
  existencia: number;
  valor: number;
}

export const fetchExistencias = (f: { q?: string; tipo?: string; estado?: string }) => apiGet<ExistenciasResponse>("/api/stock/existencias", f);
export const fetchKardex = (id: number) => apiGet<Kardex>(`/api/stock/existencias/${id}/kardex`);

export interface OpcionesBajas {
  motivos: { value: string; label: string }[];
  rubros: { idRubro: number; rubro: string }[];
  centros: { idCentro: number; centro: string }[];
  rubroPerdidas: number | null;
}

export interface Baja {
  idBaja: number;
  fecha: string | null;
  motivo: string;
  motivoLabel: string;
  detalle: string | null;
  idRubro: number;
  rubro: string | null;
  idCentro: number;
  centro: string | null;
  anulada: boolean;
  motivoAnulacion: string | null;
  renglones: { idProducto: number; producto: string | null; cantidad: number; unidadBase: string | null; costo: number | null; costoPendiente: boolean }[];
  gasto: number;
  costoPendiente: boolean;
}

export interface BajaInput {
  fecha: string;
  motivo: string;
  detalle?: string | null;
  idRubro: number;
  idCentro: number;
  renglones: { idProducto: number; cantidad: number; unidad?: string | null }[];
  confirmar?: boolean;
}

export const fetchOpcionesBajas = () => apiGet<OpcionesBajas>("/api/stock/bajas/opciones");
export const fetchBajas = (f: { fechaDesde?: string; fechaHasta?: string; motivo?: string; producto?: string; incluirAnuladas?: boolean }, page: number, pageSize = 25) =>
  apiGet<Paginado<Baja> & { gastoTotal: number }>("/api/stock/bajas", { ...f, incluirAnuladas: f.incluirAnuladas ? "true" : undefined, page, pageSize });
export const crearBaja = (input: BajaInput) => apiPost<{ idBaja: number }>("/api/stock/bajas", input);
export const anularBaja = (id: number, motivo: string) => apiPost<void>(`/api/stock/bajas/${id}/anular`, { motivo });

export interface Ajuste {
  idAjuste: number;
  fecha: string | null;
  idProducto: number;
  producto: string | null;
  cantidad: number;
  costoUnitario: number | null;
  motivo: string;
  anulado: boolean;
  motivoAnulacion: string | null;
  unidadBase: string | null;
}

export interface AjusteInput {
  fecha: string;
  idProducto: number;
  cantidad: number;
  unidad?: string | null;
  costoUnitario?: number | null;
  motivo: string;
  confirmar?: boolean;
}

export const fetchAjustes = (f: { fechaDesde?: string; fechaHasta?: string; producto?: string }, page: number, pageSize = 25) =>
  apiGet<Paginado<Ajuste>>("/api/stock/ajustes", { ...f, page, pageSize });
export const crearAjuste = (input: AjusteInput) => apiPost<{ idAjuste: number }>("/api/stock/ajustes", input);
export const anularAjuste = (id: number, motivo: string) => apiPost<void>(`/api/stock/ajustes/${id}/anular`, { motivo });

// ------------------------------------------------------------------ exportaciones (.xlsx)

function urlExport(ruta: string, params: Record<string, string | number | null | undefined>): string {
  const url = new URL(ruta, API_BASE_URL);
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
  return url.toString();
}

export const urlExportarRemitos = (f: FiltrosRemitos) =>
  urlExport("/api/remitos/exportar", { idProveedor: f.idProveedor, producto: f.producto, nroRemito: f.nroRemito, fechaDesde: f.fechaDesde, fechaHasta: f.fechaHasta, estado: f.estado });
export const urlExportarExistencias = (f: { q?: string; tipo?: string; estado?: string }) => urlExport("/api/stock/existencias/exportar", f);
export const urlExportarBajas = (f: { fechaDesde?: string; fechaHasta?: string; motivo?: string; producto?: string }) => urlExport("/api/stock/bajas/exportar", f);

// ------------------------------------------------------------------ etiquetas

export const ETIQUETA_ESTADO_FACTURA: Record<EstadoFactura, string> = { SinFactura: "Sin factura", Facturado: "Facturado" };
export const ETIQUETA_ESTADO_RENGLONES: Record<EstadoRenglones, string> = {
  SinVincular: "Sin vincular",
  Parcial: "Parcial",
  Completo: "Completo",
  ConDiferencia: "Con diferencia",
};
