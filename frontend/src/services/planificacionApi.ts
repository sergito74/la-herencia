/**
 * Planificación Agrícola: qué lote se destina a qué Cultivo/Campaña, según lo
 * definido con los asesores. Escribe exclusivamente contra `WC`.
 */

import { apiDelete, apiGet, apiPost } from "@/services/apiClient";

export interface PlanAgricolaItem {
  idPlanAgricola: number;
  idLote: number;
  numeroLote: string | null;
  superficie: number | null;
  idCultivo: number;
  cultivo: string | null;
  idCampania: number;
  campania: string | null;
}

export const fetchPlanAgricola = (idCampania?: number | null) =>
  apiGet<PlanAgricolaItem[]>("/api/planificacion", { idCampania: idCampania ?? undefined });

export const crearPlanAgricola = (datos: { idLote: number; idCultivo: number; idCampania: number }) =>
  apiPost<{ idPlanAgricola: number }>("/api/planificacion", datos);

export const eliminarPlanAgricola = (idPlanAgricola: number) => apiDelete(`/api/planificacion/${idPlanAgricola}`);
