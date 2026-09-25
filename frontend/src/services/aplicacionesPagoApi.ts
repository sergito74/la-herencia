import { apiGet, apiPost } from "@/services/apiClient";

export interface DocumentoPendiente {
  tipoDocumento: string;
  idDocumento: number;
  fecha: string | null;
  numeroDocumento: string | null;
  importeTotal: number;
  aplicado: number;
  saldoPendiente: number;
}

export interface SugerenciaItem {
  tipoDocumento: string;
  idDocumento: number;
  fecha: string | null;
  saldoPendiente: number;
  importeSugerido: number;
}

export interface SugerenciaAplicacion {
  importeMovimiento: number;
  sugerencias: SugerenciaItem[];
  saldoSinAsignar: number;
}

export interface AplicacionItem {
  tipoDocumento: string;
  idDocumento: number;
  importeAplicado: number;
}

export interface EstadoDocumento {
  importeTotal: number;
  aplicado: number;
  saldoPendiente: number;
  estado: "Pendiente" | "Parcial" | "Total";
  aplicaciones: {
    idAplicacion: number;
    importeAplicado: number;
    fecha: string;
    usuario: string;
    anulada: boolean;
    motivoAnulacion: string | null;
  }[];
}

export function fetchDocumentosPendientes(idContacto: number, tipo?: "compra" | "venta"): Promise<DocumentoPendiente[]> {
  return apiGet<DocumentoPendiente[]>("/api/aplicaciones-pago/documentos-pendientes", { idContacto, tipo });
}

export function fetchSugerencia(origenMovimiento: string, idMovimientoOrigen: number): Promise<SugerenciaAplicacion> {
  return apiPost<SugerenciaAplicacion>("/api/aplicaciones-pago/sugerir", { origenMovimiento, idMovimientoOrigen });
}

export function confirmarAplicacion(
  origenMovimiento: string,
  idMovimientoOrigen: number,
  aplicaciones: AplicacionItem[]
): Promise<{ idsAplicacion: number[] }> {
  return apiPost<{ idsAplicacion: number[] }>("/api/aplicaciones-pago", {
    origenMovimiento,
    idMovimientoOrigen,
    aplicaciones,
  });
}

export function anularAplicacion(idAplicacion: number, motivo: string): Promise<{ ok: boolean }> {
  return apiPost<{ ok: boolean }>(`/api/aplicaciones-pago/${idAplicacion}/anular`, { motivo });
}

export function fetchEstadoDocumento(tipoDocumento: string, idDocumento: number): Promise<EstadoDocumento> {
  return apiGet<EstadoDocumento>(`/api/aplicaciones-pago/documento/${tipoDocumento}/${idDocumento}`);
}

export function fetchDocumentosPendientesDeOtroContacto(
  idContacto: number,
  tipo?: "compra" | "venta"
): Promise<DocumentoPendiente[]> {
  // Mismo endpoint que fetchDocumentosPendientes: permite buscar por
  // cualquier contacto, no solo el sugerido — cubre FR-006 (aplicar a un
  // contacto distinto al del movimiento, ej. consignatario que centraliza).
  return fetchDocumentosPendientes(idContacto, tipo);
}
