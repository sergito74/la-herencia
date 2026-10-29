import { apiGet, apiPost, apiPut } from "@/services/apiClient";

export type EstadoPeriodo = "llego" | "pendiente" | "atrasada" | "baja";
export type TipoAlarma = "pago-sin-factura" | "saldo-a-favor" | "retencion-sin-factura" | "remito-sin-factura";
export type MedioPago = "galicia" | "bna" | "efectivo";

export interface FaltanteHistorico { clave: string; periodoDesde: string; periodoHasta: string; fechaEsperada: string; montoEsperado: number | null }
export interface FilaTablero {
  idContacto: number; proveedor: string; ciclo: "mensual" | "bimestral" | "trimestral"; cicloFijado: boolean; estado: EstadoPeriodo;
  periodoDesde: string; periodoHasta: string; fechaEsperada: string; montoEsperado: number | null; cambioMonto: boolean;
  ultimo: { idDeuda: number; numero: string; fecha: string; importe: number; cantidad: number } | null;
  pagoSinComprobante: { origen: MedioPago; idPago: number; fecha: string; importe: number } | null;
  faltantesHistoricos: FaltanteHistorico[];
}
export interface Tablero { hoy: string; items: FilaTablero[]; resumen: Record<EstadoPeriodo, number> }
export interface Alarma {
  clave: string; tipo: TipoAlarma; idContacto: number; proveedor: string; fecha: string; importe: number | null; detalle: string;
  origen: { medio: string; id: number } | null;
}
export interface Marca {
  idMarca: number; idContacto: number; proveedor: string; origenPago: MedioPago; idPago: number; periodoDesde: string | null;
  periodoHasta: string | null; importeAprox: number | null; estado: "abierta" | "cerrada" | "anulada"; fechaAlta: string; fechaCierre: string | null;
}

const BASE = "/api/facturas-faltantes";
export const fetchTablero = () => apiGet<Tablero>(`${BASE}/tablero`);
export const fetchAlarmas = (tipo: TipoAlarma | "", page: number) =>
  apiGet<{ items: Alarma[]; total: number; page: number; pageSize: number }>(`${BASE}/alarmas`, { ...(tipo ? { tipo } : {}), page, pageSize: 50 });
export const descartarAlarma = (clave: string, motivo: string) => apiPost<void>(`${BASE}/alarmas/${encodeURIComponent(clave)}/descartar`, { motivo });
export const fetchMarcas = (estado?: Marca["estado"]) => apiGet<Marca[]>(`${BASE}/marcas`, estado ? { estado } : {});
export const crearMarca = (body: { idContacto: number; origenPago: MedioPago; idPago: number; importeAprox?: number }) =>
  apiPost<{ idMarca: number }>(`${BASE}/marcas`, body);
export const anularMarca = (id: number, motivo: string) => apiPost<void>(`${BASE}/marcas/${id}/anular`, { motivo });
export const guardarPerfil = (idContacto: number, body: { cicloDias: 30 | 60 | 90 | null; sinCiclo: boolean; margenDias: number | null }) =>
  apiPut<void>(`${BASE}/perfil/${idContacto}`, body);
export const responderBaja = (idContacto: number, dadoDeBaja: boolean) => apiPost<void>(`${BASE}/perfil/${idContacto}/baja`, { dadoDeBaja });
export const fetchResumenMensual = () => apiGet<{ mostrar: boolean; mes: string; atrasadas: number; proveedores: string[] }>(`${BASE}/resumen-mensual`);
