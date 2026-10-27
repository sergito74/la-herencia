/**
 * Cliente de /api/boveda (042, specs/042-boveda-portales/contracts/api.md).
 * Solo para el rol Administrador (el backend responde 403 a cualquier otro).
 * Ninguna respuesta trae secretos salvo `revelar`, que no se cachea.
 */

import { apiDelete, apiGet, apiPatch, apiPost, apiPut } from "@/services/apiClient";

export type TipoPortal = "organismo" | "proveedor" | "cliente" | "banco" | "otro";
export type Titular = "empresa" | "socio";
export type Frecuencia = "desactivada" | "diaria" | "semanal" | "mensual";

export interface CredencialResumen {
  idCredencial: number;
  nombre: string;
  usuario: string | null;
  claveConfigurada: boolean;
  estado: "ok" | "faltante" | "rechazada";
}

export interface ConectorInfo {
  codigo: string | null;
  nombre: string | null;
  disponible: boolean;
  estadoCuenta: boolean;
  cargaCompras: boolean;
}

export interface Autorizacion {
  vigente: boolean;
  fecha: string | null;
  autorizadoPor: string | null;
  fuente: string | null;
  alcance: string;
}

export interface Programacion {
  frecuencia: Frecuencia;
  diaSemana: number | null;
  diaMes: number | null;
  hora: string;
  proximaCorrida: string | null;
  suspendida: boolean;
  motivoSuspension: string | null;
}

export interface Portal {
  idPortal: number;
  nombre: string;
  url: string;
  tipo: TipoPortal;
  idContacto: number | null;
  contacto: string | null;
  notas: string | null;
  credencial: CredencialResumen | null;
  conector: ConectorInfo;
  autorizacion: Autorizacion;
  programacion: Programacion | null;
  ultimaCorrida: {
    idCorrida: number;
    inicio: string;
    fin: string | null;
    estado: string;
    nuevos: number;
    existentes: number;
    cargados: number;
    pendientes: number;
    mensaje: string | null;
  } | null;
  ultimaFoto: {
    fechaCorte: string;
    moneda: "ARS" | "USD";
    saldoPortal: number;
    saldoSistema: number | null;
    diferencia: number | null;
  } | null;
  enCurso: boolean;
  /** Esperando turno en una sincronización manual (se corre de a una cuenta). */
  enCola: boolean;
  /** Paso actual y avance (n de m documentos) mientras se sincroniza. */
  progreso: { paso: string | null; hecho: number | null; total: number | null } | null;
  /** Por qué no se puede sincronizar ahora; null = se puede. */
  motivoNoSincroniza: string | null;
  /** Factura del mes que hay que bajar a mano (portales que no se pueden automatizar). */
  recordatorio: string | null;
  /** El portal no acepta navegador automático: se entra con una ventana asistida. */
  ingresoAsistido: boolean;
  asistidoAbierto: boolean;
}

export interface DatoEntrada {
  nombre: string;
  secreto: boolean;
  /** En un dato secreto existente, vacío = conservar el valor guardado. */
  valor: string | null;
}

export interface CredencialNueva {
  nombre: string;
  titular: Titular;
  idSocio: number | null;
  usuario: string | null;
  clave: string | null;
  datos: DatoEntrada[];
}

export interface Credencial {
  idCredencial: number;
  nombre: string;
  titular: Titular;
  idSocio: number | null;
  usuario: string | null;
  claveConfigurada: boolean;
  rechazada: boolean;
  datos: { nombre: string; secreto: boolean; valor: string | null }[];
  portales: number[];
}

export interface PortalEntrada {
  nombre: string;
  url: string;
  tipo: TipoPortal;
  idContacto: number | null;
  idCredencial: number | null;
  credencialNueva: CredencialNueva | null;
  codigoConector: string | null;
  notas: string | null;
}

const BASE = "/api/boveda";

export const getPortales = () => apiGet<{ items: Portal[] }>(`${BASE}/portales`);
export const getPortal = (id: number) => apiGet<Portal>(`${BASE}/portales/${id}`);
export const crearPortal = (body: PortalEntrada) => apiPost<{ idPortal: number }>(`${BASE}/portales`, body);
export const editarPortal = (id: number, body: Partial<Omit<PortalEntrada, "credencialNueva">>) =>
  apiPatch<Portal>(`${BASE}/portales/${id}`, body);
export const getConectores = () => apiGet<ConectorInfo[]>(`${BASE}/conectores`);

export const getCredenciales = () => apiGet<Credencial[]>(`${BASE}/credenciales`);
export const crearCredencial = (body: CredencialNueva) =>
  apiPost<{ idCredencial: number }>(`${BASE}/credenciales`, body);
export const editarCredencial = (
  id: number,
  body: { nombre?: string; usuario?: string | null; datos?: DatoEntrada[] }
) => apiPatch<void>(`${BASE}/credenciales/${id}`, body);
export const cambiarClave = (id: number, clave: string) =>
  apiPut<void>(`${BASE}/credenciales/${id}/clave`, { clave });
/** Devuelve el secreto en claro: no guardarlo en caché ni en estado persistente. */
export const revelar = (id: number, campo: string) =>
  apiPost<{ valor: string }>(`${BASE}/credenciales/${id}/revelar`, { campo });

export const autorizar = (id: number, body: { fecha: string; autorizadoPor: string; fuente: string | null }) =>
  apiPost<{ idAutorizacion: number }>(`${BASE}/portales/${id}/autorizacion`, body);
export const revocarAutorizacion = (id: number) => apiDelete(`${BASE}/portales/${id}/autorizacion`);

export type EstadoCarga = "cargado_auto" | "ya_cargado" | "pendiente" | "no_aplica" | "historico";

export interface Documento {
  idDocumento: number;
  idPortal: number;
  portal: string;
  tipo: string;
  proveedor: string;
  idContacto: number | null;
  fechaDocumento: string | null;
  numeroDocumento: string | null;
  totalImpreso: number | null;
  moneda: "ARS" | "USD" | null;
  ruta: string | null;
  nombreArchivo: string | null;
  estadoCarga: EstadoCarga;
  motivo: string | null;
  idCompra: number | null;
  idCorrida: number | null;
}

export interface Corrida {
  idCorrida: number;
  idPortal: number;
  portal: string;
  origen: "programada" | "manual" | "migrada037";
  usuario: string | null;
  inicio: string;
  fin: string | null;
  estado: string;
  nuevos: number;
  existentes: number;
  cargados: number;
  pendientes: number;
  mensaje: string | null;
  paso: string | null;
  avanceHecho: number | null;
  avanceTotal: number | null;
}

export interface Foto {
  idFoto: number;
  idPortal: number;
  portal: string;
  idCorrida: number | null;
  idContacto: number | null;
  fechaCorte: string;
  moneda: "ARS" | "USD";
  saldoPortal: number;
  saldoSistema: number | null;
  diferencia: number | null;
  completa: boolean;
  revisada: boolean;
  creado: string;
  movimientos?: {
    fecha: string | null;
    comprobante: string | null;
    detalle: string | null;
    debe: number | null;
    haber: number | null;
    saldo: number | null;
  }[];
}

export interface Pagina<T> {
  items: T[];
  total: number;
}

export interface ResumenBoveda {
  pendientesCarga: number;
  conError: number;
  requiereIntervencion: number;
  diferenciasSaldo: number;
  facturasAMano: number;
  total: number;
}

export const programar = (
  id: number,
  body: { frecuencia: Frecuencia; diaSemana: number | null; diaMes: number | null; hora: string }
) => apiPut<Portal>(`${BASE}/portales/${id}/programacion`, body);
export interface ResultadoSincronizar {
  encolados: number[];
  omitidos: { idPortal: number; nombre: string; motivo: string }[];
}

export const entrarConAyuda = (id: number) => apiPost<{ abierto: boolean }>(`${BASE}/portales/${id}/asistido`, {});
export const correrAhora = (id: number) => apiPost<{ encolados: number[] }>(`${BASE}/portales/${id}/corridas`, {});
/** Sincroniza ahora las cuentas elegidas (sin ids = todas las que se pueden), de a una. */
export const sincronizar = (idsPortales?: number[]) =>
  apiPost<ResultadoSincronizar>(`${BASE}/corridas`, { idsPortales: idsPortales ?? null });
export const getCorridas = (idPortal?: number, limite = 20, desde = 0) =>
  apiGet<Pagina<Corrida>>(`${BASE}/corridas`, { idPortal, limite, desde });
export const getDocumentos = (idPortal?: number, estado?: EstadoCarga, limite = 50, desde = 0) =>
  apiGet<Pagina<Documento>>(`${BASE}/documentos`, { idPortal, estado, limite, desde });
export const getFotos = (idPortal?: number) => apiGet<Foto[]>(`${BASE}/estado-cuenta`, { idPortal });
export const getFoto = (idFoto: number) => apiGet<Foto>(`${BASE}/estado-cuenta/${idFoto}`);
export const marcarFotoRevisada = (idFoto: number, revisada: boolean) =>
  apiPatch<void>(`${BASE}/estado-cuenta/${idFoto}`, { revisada });
export const getResumenBoveda = () => apiGet<ResumenBoveda>(`${BASE}/resumen`);

export const ETIQUETA_CARGA: Record<EstadoCarga, string> = {
  cargado_auto: "Cargado automáticamente",
  ya_cargado: "Ya cargado",
  pendiente: "Pendiente de carga manual",
  no_aplica: "No es comprobante de compra",
  historico: "Histórico",
};

export const ETIQUETA_CORRIDA: Record<string, string> = {
  en_curso: "En curso…",
  ok: "Terminada",
  error: "Con error",
  requiere_intervencion: "Requiere intervención (captcha o código)",
  credenciales_rechazadas: "Contraseña rechazada",
  sin_autorizacion: "Sin autorización",
  sin_credenciales: "Sin credenciales",
  portal_cambio: "El portal cambió",
  incompleta: "Interrumpida",
  salteada: "Salteada (había otra en curso)",
};

/** Alta de Compras precargada para un documento pendiente (037 FR-011). */
export function urlCargarEnCompras(d: Documento): string {
  const p = new URLSearchParams();
  if (d.idContacto) p.set("idContacto", String(d.idContacto));
  p.set("proveedor", d.proveedor);
  if (d.fechaDocumento) p.set("fecha", d.fechaDocumento);
  if (d.numeroDocumento) p.set("numeroDocumento", d.numeroDocumento);
  if (d.ruta) p.set("documentoOriginal", d.ruta);
  return `/compras/nueva?${p.toString()}`;
}
