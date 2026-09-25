import { apiGet } from "@/services/apiClient";

export interface ResumenContacto {
  idContacto: number;
  razonSocial: string | null;
  aplicadosExactos: number;
  aplicadosMejorEsfuerzo: number;
  revisionManual: number;
  fueraDeAlcance: number;
}

export interface AplicacionAutomatica {
  idAplicacion: number;
  origen: string;
  origenMovimiento: string;
  idMovimientoOrigen: number;
  tipoDocumento: string;
  idDocumentoAplicado: number;
  importeAplicado: number;
  notaConciliacion: string | null;
}

export interface ExcepcionMovimiento {
  origenMovimiento: string;
  idMovimientoOrigen: number;
  subcategoria: string;
  motivo: string | null;
}

export interface DetalleContacto {
  idContacto: number;
  aplicaciones: AplicacionAutomatica[];
  excepciones: ExcepcionMovimiento[];
}

export function fetchResumenConciliacion(soloConDudas: boolean): Promise<{ contactos: ResumenContacto[] }> {
  return apiGet<{ contactos: ResumenContacto[] }>(
    "/api/conciliacion-historico/resumen",
    soloConDudas ? { soloConDudas: "true" } : {}
  );
}

export function fetchDetalleConciliacion(idContacto: number): Promise<DetalleContacto> {
  return apiGet<DetalleContacto>(`/api/conciliacion-historico/${idContacto}/detalle`);
}

export interface ComparacionSaldo {
  idContacto: number;
  razonSocial: string | null;
  saldoActual: number;
  saldoReferencia: number;
  fechaCorteReferencia: string;
  diferencia: number;
  estado: "conciliado" | "con-diferencia";
}

export function fetchSaldosConciliacion(
  estado?: "conciliado" | "con-diferencia"
): Promise<{ contactos: ComparacionSaldo[] }> {
  return apiGet<{ contactos: ComparacionSaldo[] }>(
    "/api/conciliacion-historico/saldos",
    estado ? { estado } : {}
  );
}
