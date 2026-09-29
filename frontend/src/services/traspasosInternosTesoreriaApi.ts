/**
 * Typed client for 024-traspasos-internos-tesoreria — ver
 * specs/024-traspasos-internos-tesoreria/contracts/traspasos-internos-api.md.
 */

import { apiDelete, apiGet, apiPost } from "@/services/apiClient";
import type { Medio } from "@/services/tesoreriaApi";

export interface MovimientoReferencia {
  medio: Medio;
  idMovimiento: number;
  fecha: string;
  descripcion: string | null;
  importe: number;
}

export interface EstadoTraspasoInterno {
  vinculado: boolean;
  contraparte: MovimientoReferencia | null;
  candidatas: MovimientoReferencia[];
  idEvento: number | null;
  usuario: string | null;
  fecha: string | null;
}

export function fetchEstadoTraspasoInterno(medio: Medio, idMovimiento: number): Promise<EstadoTraspasoInterno> {
  return apiGet<EstadoTraspasoInterno>(`/api/tesoreria/${medio}/movimientos/${idMovimiento}/traspaso-interno`);
}

export function postTraspasoInterno(
  medio: Medio,
  idMovimiento: number,
  body: { medioB: Medio; idMovimientoB: number }
): Promise<EstadoTraspasoInterno> {
  return apiPost<EstadoTraspasoInterno>(`/api/tesoreria/${medio}/movimientos/${idMovimiento}/traspaso-interno`, body);
}

export function deleteTraspasoInterno(medio: Medio, idMovimiento: number): Promise<void> {
  return apiDelete(`/api/tesoreria/${medio}/movimientos/${idMovimiento}/traspaso-interno`);
}
