/**
 * Typed client for /api/cuentas-socios (021 — cuentas corrientes de
 * socios/directores y condominio). Ver specs/021-cuentas-socios/contracts/api.md.
 */

import { apiGet, apiPost } from "@/services/apiClient";

export interface CompraParticularCandidata {
  idCompra: number;
  fecha: string;
  proveedor: string | null;
  numeroDocumento: string | null;
  importePersonal: number;
}

export interface MovimientoCuentaSocio {
  idMovimiento: number;
  tipo: "AsignacionGasto" | "Devolucion";
  importe: number;
  importeUSD: number;
  importeKgCarne: number;
  fecha: string;
  origen: string | null;
  idOrigen: number | null;
  proveedorOrigen: string | null;
  numeroDocumentoOrigen: string | null;
  medio: string | null;
  motivo: string | null;
  usuario: string;
  anulada: boolean;
  motivoAnulacion: string | null;
  huerfano: boolean;
}

export interface SocioConSaldo {
  idSocio: number;
  nombre: string;
  saldo: number;
}

export interface DetalleSocio {
  idSocio: number;
  nombre: string;
  saldo: number;
  saldoUSD: number;
  saldoKgCarne: number;
  movimientos: MovimientoCuentaSocio[];
}

export function fetchSocios(): Promise<{ socios: SocioConSaldo[] }> {
  return apiGet<{ socios: SocioConSaldo[] }>("/api/cuentas-socios");
}

export function fetchComprasParticularesCandidatas(proveedor?: string): Promise<{ compras: CompraParticularCandidata[] }> {
  return apiGet<{ compras: CompraParticularCandidata[] }>("/api/cuentas-socios/compras-particulares-candidatas", {
    proveedor,
  });
}

export function fetchDetalleSocio(idSocio: number): Promise<DetalleSocio> {
  return apiGet<DetalleSocio>(`/api/cuentas-socios/${idSocio}/movimientos`);
}

export function asignarGasto(idSocio: number, idCompra: number, motivo?: string): Promise<MovimientoCuentaSocio> {
  return apiPost<MovimientoCuentaSocio>(`/api/cuentas-socios/${idSocio}/asignar-gasto`, {
    idCompra,
    motivo: motivo || null,
  });
}

export function anularMovimiento(idMovimiento: number, motivo: string): Promise<MovimientoCuentaSocio> {
  return apiPost<MovimientoCuentaSocio>(`/api/cuentas-socios/movimientos/${idMovimiento}/anular`, { motivo });
}

export function registrarDevolucion(
  idSocio: number,
  params: { importe: number; fecha: string; medio: string; motivo: string }
): Promise<MovimientoCuentaSocio> {
  return apiPost<MovimientoCuentaSocio>(`/api/cuentas-socios/${idSocio}/devolucion`, params);
}
