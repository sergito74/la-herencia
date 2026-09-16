/**
 * Typed client for the /api/arrendamientos contract (see
 * specs/005-egresos-y-ventas-menores/contracts/egresos-y-ventas-menores-api.md).
 * GET-only — this module never creates, edits, or deletes datos (FR-008).
 *
 * UI term is "Arrendamiento", never "Alquiler" (terminology decision from
 * the agro-erp-frontend-specialist consultation, see plan.md), even
 * though the field/type names below mirror the underlying SQL columns.
 */

import { apiGet } from "@/services/apiClient";

export interface CobroAlquiler {
  idCobroAlquiler: number;
  numeroCuota: number | null;
  importeCuota: number | null;
  estado: string | null;
  fechaVencimiento: string | null;
}

export interface Arrendamiento {
  idAlquiler: number;
  fecha: string | null;
  inicioPeriodo: string | null;
  finPeriodo: string | null;
  contacto: string | null;
  importeTotalContrato: number | null;
  cantidadCuotas: number | null;
  cobros: CobroAlquiler[];
}

export interface ArrendamientosListResponse {
  items: Arrendamiento[];
  page: number;
  pageSize: number;
  total: number;
}

export function fetchArrendamientos(params: {
  contacto?: string;
  page?: number;
  pageSize?: number;
}): Promise<ArrendamientosListResponse> {
  return apiGet<ArrendamientosListResponse>("/api/arrendamientos", { ...params });
}
