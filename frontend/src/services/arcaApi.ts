import { apiGet, apiPut, API_BASE_URL } from "@/services/apiClient";

export interface ParteArca { subcuenta: string; deuda: string; credito: string }
export interface MovimientoArca {
  fecha: string; documento: string | null; numeroDocumento: string | null;
  origen: string; idOrigen: number; detalle: string; deuda: string; credito: string;
  deudaOriginal: string; creditoOriginal: string; saldo: string;
  partes: ParteArca[]; version: number; manual: boolean; revisarReparto: boolean; motivo: string | null;
  documentos?: {idDocumento: number; tipo: string; periodo: string | null; numero: string | null; esOriginal: boolean}[];
}
export interface ResumenArca {
  clave: string; nombre: string; deuda: string; credito: string; saldo: string; cantidad: number;
}
export interface CuentaArca {
  resumen: ResumenArca[]; saldoTotal: string; apertura: string; saldoSeleccion: string;
  items: MovimientoArca[]; total: number; page: number; pageSize: number;
}
export const fetchArca = (params: {fechaDesde?: string; fechaHasta?: string; subcuenta?: string; page: number}) =>
  apiGet<CuentaArca>("/api/arca/cuenta", params);
export const guardarArca = (m: MovimientoArca, partes: ParteArca[], motivo: string) =>
  apiPut<{version: number}>("/api/arca/clasificacion", {origen: m.origen, idOrigen: m.idOrigen, version: m.version, partes, motivo});
export const historialArca = (m: MovimientoArca) => apiGet<{version: number; reparto: string; motivo: string; usuario: string; fecha: string}[]>(
  "/api/arca/historial", {origen: m.origen, idOrigen: m.idOrigen});
export const urlDocumentoArca = (id: number) => `${API_BASE_URL}/api/arca/documentos/${id}/archivo`;
