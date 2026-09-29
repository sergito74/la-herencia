/**
 * Typed client for /api/reasignacion-contacto (022). Ver
 * specs/022-reasignacion-contacto/contracts/api.md.
 */

import { apiGet, apiPost } from "@/services/apiClient";

export interface Reasignacion {
  idReasignacion: number;
  origen: string;
  idOrigen: number;
  idContactoAnterior: number;
  idContactoNuevo: number;
  contactoAnterior: string | null;
  contactoNuevo: string | null;
  motivo: string | null;
  usuario: string;
  fecha: string;
}

export interface Candidato {
  origen: string;
  idOrigen: number;
  fecha: string;
  descripcion: string | null;
  importe: number;
  idContactoActual: number;
  contactoActual: string | null;
  idContactoSugerido: number;
  contactoSugerido: string | null;
}

export const ORIGENES_SOPORTADOS = ["Galicia", "Banco Nacion", "Tarjetas"] as const;

export function origenSoportado(origenTipo: string | null): boolean {
  return origenTipo !== null && (ORIGENES_SOPORTADOS as readonly string[]).includes(origenTipo);
}

export function reasignarMovimiento(
  origen: string,
  idOrigen: number,
  idContactoNuevo: number,
  motivo?: string
): Promise<Reasignacion> {
  return apiPost<Reasignacion>("/api/reasignacion-contacto/reasignar", {
    origen,
    idOrigen,
    idContactoNuevo,
    motivo: motivo || null,
  });
}

export function fetchHistorial(origen?: string, idOrigen?: number): Promise<{ items: Reasignacion[] }> {
  return apiGet<{ items: Reasignacion[] }>("/api/reasignacion-contacto/historial", { origen, idOrigen });
}

export function fetchCandidatos(): Promise<{ candidatos: Candidato[] }> {
  return apiGet<{ candidatos: Candidato[] }>("/api/reasignacion-contacto/candidatos");
}

export function descartarCandidato(origen: string, idOrigen: number, idContactoSugerido: number): Promise<{ ok: boolean }> {
  return apiPost<{ ok: boolean }>("/api/reasignacion-contacto/candidatos/descartar", {
    origen,
    idOrigen,
    idContactoSugerido,
  });
}
