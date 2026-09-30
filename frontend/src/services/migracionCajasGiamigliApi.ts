/**
 * Typed client for /api/migracion-cajas-giamigli (027 — cola de casos que
 * no se pudieron migrar automáticamente desde "Cajas Giamigli.xlsx" con
 * confianza). Ver specs/027-migracion-cajas-giamigli/contracts/api.md.
 */

import { apiGet } from "@/services/apiClient";

export interface CasoARevisar {
  idRevision: number;
  hoja: string;
  numeroFila: number;
  motivo: string;
  datosCrudos: string | null;
  fechaCarga: string;
  resuelto: boolean;
}

export function fetchCasosARevisar(resuelto?: boolean): Promise<{ items: CasoARevisar[]; total: number }> {
  return apiGet<{ items: CasoARevisar[]; total: number }>("/api/migracion-cajas-giamigli/revision", {
    resuelto: resuelto === undefined ? undefined : String(resuelto),
  });
}
