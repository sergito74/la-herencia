/**
 * Typed client for 023-conciliacion-tesoreria — ver
 * specs/023-conciliacion-tesoreria/contracts/conciliacion-tesoreria-api.md.
 */

import { apiGet, apiPost, apiDelete } from "@/services/apiClient";
import type { EstadoConciliacion, Medio } from "@/services/tesoreriaApi";

export interface Conciliacion {
  idConciliacion: number;
  idContacto: number;
  contacto: string | null;
  importe: number;
  usuario: string;
  fecha: string;
  tipoOrigenDocumento: OrigenDocumento | null;
  idOrigenDocumento: number | null;
}

export interface EstadoConciliacionResponse {
  estado: EstadoConciliacion;
  importeTotal: number;
  saldoPendiente: number;
  conciliaciones: Conciliacion[];
  idContactoReconocido: number | null;
  contactoReconocido: string | null;
  auditoria: AuditoriaConciliacion | null;
}

export type OrigenDocumento = "Compras" | "Impuestos" | "Remuneraciones" | "Alquileres";
export interface ReferenciaDocumento { origen: OrigenDocumento; idOrigen: number }
export interface DocumentoConciliable extends ReferenciaDocumento {
  fecha: string | null;
  tipoDocumento: string | null;
  numeroDocumento: string | null;
  moneda: string | null;
  tipoDeCambio: number | null;
  importeOriginal: number;
  importePesos: number;
  saldoPendiente: number;
  contraparte: string | null;
  vinculosPrevios: number;
}
export interface CalculoConciliacion {
  estado: "exacta" | "parcial";
  diferencia: number;
  pagoParcial: boolean;
  permiteParcial: boolean;
  imputados: (ReferenciaDocumento & { importeImputado: number })[];
  tcImplicito: number | null;
  tcReferencia: number | null;
  desvioTc: number | null;
}
export interface MotivoConciliacion { motivo: string; detalle: string | null }
export interface AuditoriaConciliacion extends MotivoConciliacion {
  idEstado: number;
  estado: "SinDocumento" | "DiferenciaAceptada";
  importeDiferencia: number | null;
  usuario: string;
  fecha: string;
}
const ruta = (medio: Medio, id: number) => `/api/tesoreria/${medio}/movimientos/${id}`;
export const buscarDocumentos = (q: string) => apiGet<DocumentoConciliable[]>(`/api/tesoreria/documentos-buscar?q=${encodeURIComponent(q)}`);
export const fetchCandidatosDocumentos = (medio: Medio, id: number) => apiGet<{
  documentos: DocumentoConciliable[];
  sugerencias: (CalculoConciliacion & { documentos: ReferenciaDocumento[] })[];
}>(`${ruta(medio,id)}/candidatos`);
export const fetchPreviewDocumentos = (medio: Medio, id: number, docs: ReferenciaDocumento[]) => {
  const q = new URLSearchParams();
  docs.forEach(d => q.append("documentos",`${d.origen}:${d.idOrigen}`));
  return apiGet<CalculoConciliacion>(`${ruta(medio,id)}/conciliacion-preview?${q}`);
};
export const postConciliacionLote = (medio: Medio, id: number, documentos: ReferenciaDocumento[], aceptarDiferencia: MotivoConciliacion | null) =>
  apiPost<Conciliacion[]>(`${ruta(medio,id)}/conciliacion-lote`,{documentos,aceptarDiferencia});
export const postSinDocumento = (medio: Medio, id: number, motivo: MotivoConciliacion) => apiPost<void>(`${ruta(medio,id)}/sin-documento`,motivo);
export const quitarEstadoConciliacion = (medio: Medio, id: number) => apiDelete(`${ruta(medio,id)}/estado`);
export const quitarConciliacion = (medio: Medio, id: number, idConciliacion: number) =>
  apiDelete(`${ruta(medio,id)}/conciliacion/${idConciliacion}`);

export function fetchEstadoConciliacion(
  medio: Medio,
  idMovimiento: number
): Promise<EstadoConciliacionResponse> {
  return apiGet<EstadoConciliacionResponse>(`/api/tesoreria/${medio}/movimientos/${idMovimiento}/conciliacion`);
}

export function postConciliacion(
  medio: Medio,
  idMovimiento: number,
  body: { idContacto: number; importe: number }
): Promise<Conciliacion> {
  return apiPost<Conciliacion>(`/api/tesoreria/${medio}/movimientos/${idMovimiento}/conciliacion`, body);
}
