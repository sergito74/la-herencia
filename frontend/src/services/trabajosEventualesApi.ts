import { apiGet, apiPost, apiPatch, apiDelete } from "./apiClient";

export interface TrabajoInput {
  idContacto: number; fecha: string; descripcion: string; dias: number; jornal: number; viaticos: number;
  redondeo: number; estadoPago: "Pendiente" | "Pagado"; numeroRecibo: string | null; observaciones: string | null;
}
export interface Trabajo extends TrabajoInput {
  idTrabajo: number; trabajador: string; total: number; vinculado: number; sinVincular: number; origen: string | null;
  vinculos?: { idSalario: number; importe: number; periodo: string; fecha: string }[];
}
export interface ListaTrabajos {
  items: Trabajo[]; total: number; page: number; pageSize: number;
  resumen: { cantidad: number; totalTrabajos: number; totalVinculado: number; sinVincular: number };
}
export interface LiquidacionCandidata { idSalario: number; periodo: string; fecha: string; neto: number; disponible: number }
export type Filtros = { idContacto?: number; desde?: string; hasta?: string; estadoPago?: string; vinculacion?: string; idSalario?: number; page?: number };
const base = "/api/trabajos-eventuales";
export const listarTrabajos = (params: Filtros) => apiGet<ListaTrabajos>(base, params);
export const obtenerTrabajo = (id: number) => apiGet<Trabajo>(`${base}/${id}`);
export const liquidacionesTrabajo = (id: number) => apiGet<LiquidacionCandidata[]>(`${base}/${id}/liquidaciones`);
export const guardarTrabajo = (datos: TrabajoInput, id?: number) => id ? apiPatch<Trabajo>(`${base}/${id}`, datos) : apiPost<Trabajo>(base, datos);
export const vincularTrabajo = (id: number, idSalario: number, importe: number) => apiPost<Trabajo>(`${base}/${id}/vinculos`, { idSalario, importe });
export const desvincularTrabajo = (id: number, idSalario: number) => apiDelete(`${base}/${id}/vinculos/${idSalario}`);
