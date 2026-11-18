import { apiGet, apiPost, apiPatch, apiDelete } from "./apiClient";

export interface TrabajoInput {
  idContacto: number; fecha: string; descripcion: string; dias: number; jornal: number; viaticos: number;
  redondeo: number; estadoPago: "Pendiente" | "Pagado"; numeroRecibo: string | null; observaciones: string | null;
}
export interface Trabajo extends TrabajoInput {
  idTrabajo: number; trabajador: string; total: number; vinculado: number; sinVincular: number; origen: string | null;
  vinculos?: { idSalario: number; importe: number; periodo: string; fecha: string }[];
  pagos?: PagoTrabajoItem[]; pagado?: number;
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

// Pagos (04/11/2026): efectivo desde una caja (gasto sin comprobante) o transferencia ya cargada del banco.
export interface PagoTrabajoItem { idPago: number; medio: "caja" | "galicia" | "bna" | "socio"; caja: string | null; fecha: string; importe: number; socio?: string | null; banco?: string | null }
export interface PagoSocioInput { idSocio: number; fecha: string; importe: number; medio: string }
export interface PagoCajaInput {
  caja: "giamigli-sa" | "campo-chica" | "condominio-lsc"; fecha: string; importe: number; cuenta: "A" | "B";
  idRubro: number; idCentroCostos: number; idCampania: number | null; previewVersion?: string; advertenciasAceptadas?: string[];
}
export interface PreviewPagoTrabajo { previewVersion: string; advertencias: string[]; efectosPrevistos: { caja: string; importe: string; saldoResultante: string }[] }
export interface TransferenciaTrabajo { medio: "galicia" | "bna"; id: number; fecha: string; importe: number; detalle: string | null }
export const previsualizarPagoTrabajo = (id: number, d: PagoCajaInput) => apiPost<PreviewPagoTrabajo>(`${base}/${id}/pagos/caja/previsualizar`, d);
export const pagarTrabajoCaja = (id: number, d: PagoCajaInput) => apiPost<Trabajo>(`${base}/${id}/pagos/caja`, d);
export const transferenciasTrabajo = (id: number) => apiGet<TransferenciaTrabajo[]>(`${base}/${id}/pagos/transferencias`);
export const pagarTrabajoTransferencia = (id: number, medio: string, idMovimiento: number) => apiPost<Trabajo>(`${base}/${id}/pagos/transferencia`, { medio, idMovimiento });
export const quitarPagoTrabajo = (id: number, idPago: number) => apiDelete(`${base}/${id}/pagos/${idPago}`);
export const pagarTrabajoSocio = (id: number, d: PagoSocioInput) => apiPost<Trabajo>(`${base}/${id}/pagos/socio`, d);

// 18/11/2026: un solo pago para varios trabajos del mismo trabajador (se reparte del más viejo al más nuevo).
export const transferenciasVarios = (ids: number[]) => apiGet<TransferenciaTrabajo[]>(`${base}/pagos-varios/transferencias`, { ids: ids.map(String) });
export const pagarVariosSocio = (ids: number[], d: PagoSocioInput) => apiPost<Trabajo[]>(`${base}/pagos-varios/socio`, { ...d, idsTrabajo: ids });
export const pagarVariosTransferencia = (ids: number[], medio: string, idMovimiento: number) =>
  apiPost<Trabajo[]>(`${base}/pagos-varios/transferencia`, { medio, idMovimiento, idsTrabajo: ids });
export const previsualizarPagoVarios = (ids: number[], d: PagoCajaInput) => apiPost<PreviewPagoTrabajo>(`${base}/pagos-varios/caja/previsualizar`, { ...d, idsTrabajo: ids });
export const pagarVariosCaja = (ids: number[], d: PagoCajaInput) => apiPost<Trabajo[]>(`${base}/pagos-varios/caja`, { ...d, idsTrabajo: ids });
