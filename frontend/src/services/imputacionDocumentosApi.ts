import { apiGet, apiPost } from "./apiClient";

/** Pantalla "Documentos" de imputación (auditoría de diseño 18/11/2026, spec 051). */
export type EstadoDoc = "decision" | "revisar" | "pendiente" | "aprobado";
export type Familia = "agricultura" | "ganaderia" | "administracion" | "stock" | "aviso";

export interface DestinoDoc { clave: string; etiqueta: string; familia: Familia; importe: number; porcentaje: number | null }
export interface DocumentoFila {
  idCompra: number; fecha: string; idContacto: number | null; proveedor: string | null; tipoDocumento: string | null;
  numeroDocumento: string | null; moneda: string; importe: number; estado: EstadoDoc; estadoTexto: string;
  motivo: string | null; corridasPendientes: string[]; destinos: DestinoDoc[];
}
export interface ResumenDocumentos {
  items: DocumentoFila[]; total: number; importe: number;
  porEstado: { clave: EstadoDoc; etiqueta: string; cantidad: number; importe: number }[];
  porDestino: (DestinoDoc & { cantidad: number })[];
  porProveedor: { idContacto: number | null; proveedor: string; importe: number; cantidad: number }[];
}
export interface FiltrosDocumentos {
  idContacto?: number | null; fechaDesde?: string; fechaHasta?: string; estado?: EstadoDoc | ""; destino?: string; page: number; pageSize: number;
}
export interface FraccionDetalle {
  idPropuesta: number; idCorrida: string; origen: string; lote: string | null; destino: string; importe: number;
  estado: "Pendiente" | "Aprobada" | "RequiereIntervencion"; cantidad: number | null; unidad: string | null;
}
export interface LineaDetalle {
  idDetalleCompra: number; producto: string; cantidad: number | null; unidad: string | null; campaniaManual: string | null;
  centroCostoManual: string | null; rubroManual: string | null; enRepartoOrdenes?: boolean; totalFracciones: number; fracciones: FraccionDetalle[];
}
export interface DocumentoDetalle {
  idCompra: number; fecha: string; proveedor: string | null; tipoDocumento: string | null; numeroDocumento: string | null;
  moneda: string; tipoDeCambio: number | null; importe: number; motivo: string | null; lineas: LineaDetalle[];
}

const limpio = (f: FiltrosDocumentos) => ({
  idContacto: f.idContacto ?? undefined, fechaDesde: f.fechaDesde || undefined, fechaHasta: f.fechaHasta || undefined,
  estado: f.estado || undefined, destino: f.destino || undefined, page: f.page, pageSize: f.pageSize,
});
export const fetchResumenDocumentos = (f: FiltrosDocumentos) => apiGet<ResumenDocumentos>("/api/imputacion/documentos-resumen", limpio(f));
export const fetchDocumentoDetalle = (id: number) => apiGet<DocumentoDetalle>(`/api/imputacion/documentos-resumen/${id}`);
export const aprobarCorridas = (idCorridas: string[]) =>
  apiPost<{ aprobadas: number; fallidas: number }>("/api/imputacion/propuestas/aprobar-lote", { idCorridas });
