/**
 * Documentos nuevos (043): lo que el sistema incorporó solo (portales y mails) y falta revisar.
 * Contrato en specs/043-rutina-documentos-nuevos/contracts/api.md.
 */

import { apiGet, apiPost } from "@/services/apiClient";

const BASE = "/api/documentos-nuevos";

export type ModuloAviso = "compras" | "impuestos" | "ventas" | "tesoreria" | "cuentas_corrientes" | "sin_clasificar" | "pagos";

export interface ResumenNuevos {
  pagos: number;
  compras: number;
  impuestos: number;
  ventas: number;
  tesoreria: number;
  cuentasCorrientes: number;
  sinClasificar: number;
  total: number;
}

export interface RenglonNuevo {
  detalle: string | null;
  rubro: string | null;
  centroCosto: string | null;
  importe: number | null;
  iva: number | null;
}

export interface DocumentoNuevo {
  idDocumentoNuevo: number;
  origen: string;
  origenDetalle: string | null;
  tipo: string;
  modulo: ModuloAviso;
  estado: "cargado_solo" | "para_cargar";
  motivo: string | null;
  contacto: string | null;
  idContacto: number | null;
  fecha: string | null;
  numero: string | null;
  total: number | null;
  archivo: string;
  ruta: string;
  idRegistro: number | null;
  enlace: string | null;
  renglones: RenglonNuevo[] | null;
}

export interface EstadoRutina {
  proxima: string | null;
  activa: boolean;
  ultima: {
    inicio: string | null;
    fin: string | null;
    estado: "en_curso" | "ok" | "con_problemas" | "incompleta";
    cuentasCorridas: number;
    cuentasConProblemas: number;
    mailsLeidos: number;
    documentosNuevos: number;
    cargadosSolos: number;
    paraCargarAMano: number;
    mensaje: string | null;
  } | null;
}

export const ETIQUETA_MODULO: Record<ModuloAviso, string> = {
  pagos: "Pagos y recibos",
  compras: "Compras",
  impuestos: "Impuestos y retenciones",
  ventas: "Ventas",
  tesoreria: "Tesorería",
  cuentas_corrientes: "Cuentas corrientes",
  sin_clasificar: "Sin clasificar",
};

export const getResumenNuevos = () => apiGet<ResumenNuevos>(`${BASE}/resumen`);
export const getNuevos = (modulo: ModuloAviso, limite = 50, desde = 0) =>
  apiGet<{ items: DocumentoNuevo[]; total: number }>(`${BASE}/`, { modulo, limite, desde });
export const marcarNuevoRevisado = (id: number) => apiPost<{ ok: boolean }>(`${BASE}/${id}/revisado`, {});
export const moverNuevo = (id: number, modulo: ModuloAviso) =>
  apiPost<DocumentoNuevo>(`${BASE}/${id}/modulo`, { modulo });
export const getEstadoRutina = () => apiGet<EstadoRutina>(`${BASE}/rutina`);
