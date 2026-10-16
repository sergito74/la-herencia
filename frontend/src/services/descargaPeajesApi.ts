/**
 * Cliente de /api/descarga-peajes (037, specs/037-descarga-peajes/contracts/api.md).
 * El POST lo rechaza el backend con 403 para el rol Lectura y con 409 si ya
 * hay una descarga en curso.
 */

import { apiGet, apiPost } from "@/services/apiClient";

export type EstadoEjecucion = "en_curso" | "completa" | "con_errores" | "incompleta" | "salteada";
export type EstadoPortal = "pendiente" | "en_curso" | "ok" | "error" | "sin_credenciales";
export type EstadoCarga = "cargado_auto" | "ya_cargado" | "pendiente" | "historico";

export interface EstadoConfiguracion {
  portales: { portal: string; credenciales: boolean }[];
  tarea: { instalada: boolean; proximaCorrida: string | null; ultimoResultado: string | null };
  enCurso: { idEjecucion: number; inicio: string; origen: string } | null;
}

export interface PortalResultado {
  portal: string;
  estado: EstadoPortal;
  nuevos: number;
  existentes: number;
  cargados: number;
  pendientes: number;
  error: string | null;
}

export interface DocumentoPeaje {
  idDocumento: number;
  portal: string;
  proveedor: string;
  idContacto: number | null;
  fechaDocumento: string | null;
  numeroDocumento: string | null;
  totalImpreso: number | null;
  ruta: string | null;
  nombreArchivo: string | null;
  estadoCarga: EstadoCarga;
  motivo: string | null;
  idCompra: number | null;
  idEjecucion: number | null;
}

export interface Ejecucion {
  idEjecucion: number;
  origen: "manual" | "semanal";
  usuario: string | null;
  inicio: string;
  fin: string | null;
  estado: EstadoEjecucion;
  mensaje: string | null;
  portales: PortalResultado[];
}

export interface EjecucionDetalle extends Ejecucion {
  documentos: DocumentoPeaje[];
}

export interface Pagina<T> {
  items: T[];
  total: number;
}

export const getEstado = () => apiGet<EstadoConfiguracion>("/api/descarga-peajes/estado");

export const iniciarDescarga = () => apiPost<{ idEjecucion: number }>("/api/descarga-peajes/ejecuciones", {});

export const getEjecucion = (id: number) => apiGet<EjecucionDetalle>(`/api/descarga-peajes/ejecuciones/${id}`);

export const getEjecuciones = (limite = 20, desde = 0) =>
  apiGet<Pagina<Ejecucion>>("/api/descarga-peajes/ejecuciones", { limite, desde });

export const getDocumentos = (estado?: Exclude<EstadoCarga, "historico">, limite = 50, desde = 0) =>
  apiGet<Pagina<DocumentoPeaje>>("/api/descarga-peajes/documentos", { estado, limite, desde });

export const getResumen = () =>
  apiGet<{ pendientes: number; portalesConError: number }>("/api/descarga-peajes/resumen");

/** Alta de Compras precargada para un documento pendiente (FR-011). */
export function urlCargarEnCompras(d: DocumentoPeaje): string {
  const p = new URLSearchParams();
  if (d.idContacto) p.set("idContacto", String(d.idContacto));
  p.set("proveedor", d.proveedor);
  if (d.fechaDocumento) p.set("fecha", d.fechaDocumento);
  if (d.numeroDocumento) p.set("numeroDocumento", d.numeroDocumento);
  if (d.ruta) p.set("documentoOriginal", d.ruta);
  return `/compras/nueva?${p.toString()}`;
}

export const ETIQUETA_PORTAL: Record<EstadoPortal, string> = {
  pendiente: "Pendiente",
  en_curso: "En curso…",
  ok: "Terminado",
  error: "Con error",
  sin_credenciales: "Sin configurar",
};

export const ETIQUETA_EJECUCION: Record<EstadoEjecucion, string> = {
  en_curso: "En curso",
  completa: "Completa",
  con_errores: "Con errores",
  incompleta: "Incompleta",
  salteada: "Salteada (había otra en curso)",
};

export const ETIQUETA_CARGA: Record<EstadoCarga, string> = {
  cargado_auto: "Cargado automáticamente",
  ya_cargado: "Ya cargado",
  pendiente: "Pendiente de carga manual",
  historico: "Histórico",
};
