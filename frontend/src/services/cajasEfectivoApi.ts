/**
 * Typed client for /api/cajas-efectivo (027 — cajas de efectivo de
 * Giamigli SA y del campo). Ver specs/027-migracion-cajas-giamigli/contracts/api.md.
 */

import { apiGet } from "@/services/apiClient";

export type CajaSlug = "giamigli-sa" | "campo-chica";

export interface MovimientoCajaEfectivo {
  idMovimiento: number;
  fecha: string;
  concepto: string | null;
  detalle: string | null;
  importe: number;
  cuenta: string | null;
  formaPago: string | null;
  numeroDocumento: string | null;
  idContactoRelacionado: number | null;
}

export interface SaldoCaja {
  caja: CajaSlug;
  saldo: number;
}

export interface MovimientosCajaResponse {
  items: MovimientoCajaEfectivo[];
  page: number;
  pageSize: number;
  total: number;
}

export function fetchSaldoCaja(caja: CajaSlug): Promise<SaldoCaja> {
  return apiGet<SaldoCaja>(`/api/cajas-efectivo/${caja}/saldo`);
}

export function fetchMovimientosCaja(
  caja: CajaSlug,
  params: { page: number; pageSize: number }
): Promise<MovimientosCajaResponse> {
  return apiGet<MovimientosCajaResponse>(`/api/cajas-efectivo/${caja}/movimientos`, {
    page: params.page,
    pageSize: params.pageSize,
  });
}
