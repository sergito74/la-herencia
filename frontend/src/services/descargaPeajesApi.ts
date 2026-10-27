/**
 * Cliente de /api/descarga-peajes (037; desde 042 sobre la Bóveda de portales,
 * specs/042-boveda-portales/contracts/api.md "Compatibilidad 037").
 * Vista de Compras de los 4 portales de peaje: no requiere Administrador y no
 * trae credenciales. El POST lo rechaza el backend con 403 para el rol Lectura
 * y con 409 si ya hay una descarga en curso.
 */

import { apiGet, apiPost } from "@/services/apiClient";
import type { Corrida, Documento, Pagina } from "@/services/bovedaApi";

export interface PortalPeaje {
  idPortal: number;
  portal: string;
  credenciales: boolean;
  autorizado: boolean;
  proximaCorrida: string | null;
  ultimaCorrida: { estado: string; inicio: string } | null;
}

export interface EstadoPeajes {
  portales: PortalPeaje[];
  enCurso: boolean;
}

export const getEstado = () => apiGet<EstadoPeajes>("/api/descarga-peajes/estado");

export const iniciarDescarga = () => apiPost<{ portales: number[] }>("/api/descarga-peajes/ejecuciones", {});

export const getCorridas = (limite = 20, desde = 0) =>
  apiGet<Pagina<Corrida>>("/api/descarga-peajes/corridas", { limite, desde });

export const getDocumentos = (estado?: "pendiente" | "cargado_auto" | "ya_cargado", limite = 50, desde = 0) =>
  apiGet<Pagina<Documento>>("/api/descarga-peajes/documentos", { estado, limite, desde });

export const getResumen = () =>
  apiGet<{ pendientes: number; portalesConError: number }>("/api/descarga-peajes/resumen");
