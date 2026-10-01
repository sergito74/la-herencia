import { apiGet, apiPatch, apiPost } from "@/services/apiClient";

// 031 — Integridad de vínculos (specs/031-integridad-vinculos/contracts/api.md)

export type CategoriaHallazgo =
  | "documento-excedido"
  | "movimiento-excedido"
  | "doble-imputacion"
  | "fecha-incoherente"
  | "moneda-mezclada";

export interface HallazgoIntegridad {
  categoria: CategoriaHallazgo;
  tipoDocumento: string | null;
  idDocumento: number | null;
  origenMovimiento: string | null;
  idMovimiento: number | null;
  totalDocumento: number | null;
  imputadoPorVia: Record<string, number>;
  exceso: number | null;
  diasAntes: number | null;
  idAplicacion: number | null;
  importe: number | null;
  fechaDocumento: string | null;
  idContacto: number | null;
}

export interface ControlIntegridad {
  generado: string;
  totales: Record<CategoriaHallazgo, number>;
  hallazgos: HallazgoIntegridad[];
}

export interface GrupoLote {
  grupo: string;
  accion: "anular" | "pesificar" | "reemplazo";
  cantidad: number;
  incluidos: number;
  importe: number;
}

export interface CandidatoReemplazo {
  origenMovimiento: string;
  idMovimientoOrigen: number;
  tipoDocumento: string;
  idDocumento: number;
  fecha: string | null;
  libre: number;
}

export interface ItemLote {
  idItem: number;
  grupo: string;
  accion: "anular" | "pesificar" | "reemplazo";
  idAplicacion: number | null;
  origenMovimiento: string | null;
  idMovimientoOrigen: number | null;
  tipoDocumento: string | null;
  idDocumento: number | null;
  importe: number | null;
  motivo: string;
  candidatos: CandidatoReemplazo[] | null;
  incluido: boolean;
  elegido: boolean;
  idAplicacionCreada: number | null;
}

export interface Lote {
  idLote: number;
  estado: "propuesto" | "aplicado" | "revertido" | "descartado";
  fechaPropuesta: string;
  fechaAplicado: string | null;
  fechaRevertido: string | null;
  usuario: string;
  backupArchivo: string | null;
  grupos: GrupoLote[];
  ambiguosSinElegir: number;
  items: ItemLote[];
}

export type LoteResumen = Pick<Lote, "idLote" | "estado" | "fechaPropuesta" | "fechaAplicado" | "fechaRevertido" | "usuario">;

const BASE = "/api/integridad-vinculos";

export const fetchControl = (categoria?: CategoriaHallazgo) =>
  apiGet<ControlIntegridad>(`${BASE}/control`, { categoria });

export const fetchLotes = () => apiGet<LoteResumen[]>(`${BASE}/lotes`);

export const fetchLote = (idLote: number, grupo?: string, pagina = 1) =>
  apiGet<Lote>(`${BASE}/lotes/${idLote}`, { grupo, pagina, tamanio: 100 });

export const crearLote = () => apiPost<{ idLote: number }>(`${BASE}/lotes`, {});

export const actualizarItems = (
  idLote: number,
  cambios: {
    incluir?: number[];
    excluir?: number[];
    elegir?: { idItem: number; candidato: number }[];
    incluirGrupo?: string;
    excluirGrupo?: string;
  }
) => apiPatch<{ grupos: GrupoLote[]; ambiguosSinElegir: number }>(`${BASE}/lotes/${idLote}/items`, cambios);

export const aplicarLote = (idLote: number) =>
  apiPost<{ anuladas: number; creadas: number; backup: string }>(`${BASE}/lotes/${idLote}/aplicar`, {});

export const revertirLote = (idLote: number) =>
  apiPost<{ reactivadas: number; anuladas: number }>(`${BASE}/lotes/${idLote}/revertir`, {});

export const descartarLote = (idLote: number) => apiPost<{ ok: boolean }>(`${BASE}/lotes/${idLote}/descartar`, {});

// --- Revisión por proveedor ---

export interface ProveedorLote {
  idContacto: number;
  nombre: string;
  cambios: number;
  importe: number;
  facturas: number;
  reemplazosPorElegir: number;
  estado: "pendiente" | "aprobado" | "rechazado";
}

export interface PagoDescripto {
  medio: string;
  fecha: string | null;
  concepto: string;
  importe: number | null;
}

export interface PagoFactura extends PagoDescripto {
  via: string;
  imputado: number;
  imputadoDespues: number | null;
  cambio: "se mantiene" | "se quita" | "se agrega" | "se pesifica";
  motivo: string | null;
}

export interface FacturaRevision {
  tipoDocumento: string;
  idDocumento: number;
  numero: string;
  fecha: string | null;
  moneda: string | null;
  total: number | null;
  totalOriginal: number | null;
  tc: number | null;
  pagadoAntes: number;
  pagadoDespues: number;
  saldoAntes: number | null;
  saldoDespues: number | null;
  pagos: PagoFactura[];
}

export interface DetalleProveedor {
  idContacto: number;
  nombre: string;
  estado: ProveedorLote["estado"];
  facturas: FacturaRevision[];
  pagosLibres: (PagoDescripto & { liberado: number; motivo: string })[];
  reemplazosPorElegir: {
    idItem: number;
    motivo: string;
    importe: number;
    elegido: boolean;
    candidatos: (CandidatoReemplazo & { pago: PagoDescripto; numero: string | null; elegidoActual: boolean })[];
  }[];
}

export const fetchProveedoresLote = (idLote: number) => apiGet<ProveedorLote[]>(`${BASE}/lotes/${idLote}/proveedores`);

export const fetchDetalleProveedor = (idLote: number, idContacto: number) =>
  apiGet<DetalleProveedor>(`${BASE}/lotes/${idLote}/proveedores/${idContacto}`);

export const decidirProveedor = (idLote: number, idContacto: number, aprobar: boolean) =>
  apiPost<{ estado: string }>(`${BASE}/lotes/${idLote}/proveedores/${idContacto}/decision`, { aprobar });
