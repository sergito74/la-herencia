/**
 * Revisión sistemática de cuentas — 036-revision-sistematica-cuentas.
 * Ver specs/036-revision-sistematica-cuentas/contracts/revision-cuentas-api.md.
 */

import { apiDelete, apiGet, apiPost, apiPut } from "@/services/apiClient";

const BASE = "/api/revision-cuentas";

export type Cola = "A" | "B" | "C" | "D" | "E" | "F" | "G" | "H" | "I";
export type Etapa = "E0" | "E1" | "E2" | "E3" | "E4" | "E5" | "E6";
export type EstadoFicha =
  | "pendiente"
  | "en-proceso"
  | "esperando-evidencia"
  | "esperando-sergio"
  | "cerrada"
  | "cerrada-con-excepcion";
export type EstadoEfectivo = EstadoFicha | "reabierta";
export type EstadoMarca = "pendiente" | "factura-cargada" | "sin-documento" | "anticipo" | "venta-cargada";
export type TipoVenta = "venta-hacienda" | "venta-granos" | "arrendamiento";
export type FuenteSaldoExterno = "portal" | "pdf" | "mail" | "banco" | "tarjeta" | "sin-estado";
export type FuenteRespaldo = "portal" | "estado-de-cuenta" | "pdf";
export type Moneda = "Pesos" | "Dolares";

// ---- Corte

export interface Corte {
  corte: string;
  motivo: string | null;
  usuario: string;
  fecha: string;
}

// ---- Tablero

export interface CasillaTablero {
  cola: Cola;
  etapa: Etapa;
  cuentas: number;
  importe: number;
}

export interface ComparacionTablero {
  semanaAnterior: string;
  cerradasEnLaSemana: number;
  variacionExcepciones: number;
}

export interface Tablero {
  corte: string;
  totalCuentas: number;
  porEstado: Record<EstadoEfectivo, number>;
  casillas: CasillaTablero[];
  totalesPorCola: Record<string, { cuentas: number; importe: number }>;
  comparacion: ComparacionTablero | null;
  preguntas: number;
}

export interface FotoTablero {
  idFoto: number;
  semana: string;
  corte: string;
  fecha: string;
  totalCuentas: number;
}

export interface Pregunta {
  idContacto: number;
  razonSocial: string;
  cola: Cola;
  etapa: Etapa;
  pregunta: string;
  desde: string;
}

// ---- Colas y lotes

export interface CuentaDeCola {
  idContacto: number;
  razonSocial: string;
  movimientos: number;
  importe: number;
  saldo: number;
  moneda: Moneda;
  etapa: Etapa;
  estado: EstadoEfectivo;
  otrosProblemas: string[];
}

export interface ColaCuentas {
  cola: Cola;
  total: number;
  pagina: number;
  cuentas: CuentaDeCola[];
}

export interface ReglaLote {
  regla: string;
  cola: Cola;
  descripcion: string;
}

export interface CuentaDeLote {
  idContacto: number;
  razonSocial: string;
  tildada: boolean;
  cumple: boolean;
  saldoAntes: number;
  saldoDespues: number;
  detalle: string;
}

export interface Lote {
  idCorreccion: number;
  regla: string;
  cola: Cola;
  estado: "simulada" | "aplicada" | "revertida" | "descartada";
  cuentas: CuentaDeLote[];
  respaldo?: string | null;
}

// ---- Ficha

export interface Criterio {
  codigo: "C1" | "C2" | "C3" | "C4" | "C5" | "C6" | "C7";
  etapa: Etapa;
  cumple: boolean | null;
  medido: string;
  texto: string;
  /** Fuente de la evidencia cuando C3 se cumple (por ejemplo "access", "portal" o "sin-estado"). */
  evidencia?: string | null;
}

export interface EntradaHistorial {
  accion: string;
  detalle: string | null;
  usuario: string | null;
  fecha: string;
}

export interface Ficha {
  idContacto: number;
  razonSocial: string;
  corte: string;
  estado: EstadoFicha;
  estadoEfectivo: EstadoEfectivo;
  etapa: Etapa;
  cola: Cola;
  otrosProblemas: string[];
  saldoAlCorte: number;
  moneda: Moneda;
  saldoEsperado: "cero" | "puede-tener-saldo" | null;
  criterios: Criterio[];
  inventarioFuentes: unknown | null;
  pagosSinFactura: number;
  saldosExternos: number;
  antecedente035: { estado: string; nota: string | null; fecha: string | null } | null;
  fifoAplicadoAntes: boolean;
  pregunta: string | null;
  cierre: { corte: string; saldoAlCierre: number; usuario: string | null; fecha: string | null; conExcepcion: boolean; motivoExcepcion?: string | null } | null;
  historial: EntradaHistorial[];
}

export interface CambioFicha {
  estado: Exclude<EstadoFicha, "pendiente">;
  nota?: string | null;
  motivoExcepcion?: string | null;
  pregunta?: string | null;
}

export interface FuenteInventario {
  tipo: "estado-proveedor" | "extracto" | "resumen-tarjeta" | "certificado" | "dropbox" | "access";
  disponible: boolean;
  detalle?: string | null;
}

export interface Decision {
  idDecision: number;
  tipo: "descartar-access" | "cierre-con-excepcion" | "otro";
  texto: string;
  evidencia: string | null;
  usuario: string;
  fecha: string;
}

// ---- Pagos sin factura

export interface PagoSinFactura {
  medio: string;
  idMovimiento: number;
  fecha: string;
  importe: number;
  retencionAsociada: number | null;
  importeEsperadoFactura: number;
  fechaEsperadaDesde: string;
  fechaEsperadaHasta: string;
  confianza: "alta" | "media";
  anteriorA2021: boolean;
  marca: {
    estado: EstadoMarca;
    nota: string | null;
    idCompra: number | null;
    fuenteRespaldo: FuenteRespaldo | null;
    tipoVenta?: TipoVenta | null;
    idVenta?: number | null;
    respaldo?: string | null; // por ejemplo "venta de hacienda 00003-00000014"
  } | null;
}

export interface FacturaSinPago {
  idCompra: number;
  numero: string;
  fecha: string;
  importe: number;
}

export interface PagosSinFactura {
  idContacto: number;
  corte: string;
  consistencia: { pagosSinFactura: number; facturasSinPago: number; saldo: number; cierra: boolean; sinApertura?: boolean };
  pagos: PagoSinFactura[];
  facturasSinPago: FacturaSinPago[];
}

export interface MarcaPagoSinFactura {
  estado: EstadoMarca;
  idCompra?: number | null;
  fuenteRespaldo?: FuenteRespaldo | null;
  tipoVenta?: TipoVenta | null;
  idVenta?: number | null;
  nota?: string | null;
}

export interface VentaDeCuenta {
  tipo: TipoVenta;
  idVenta: number;
  fecha: string;
  numero: string | null;
  rotulo: string;
}

// ---- Evidencia externa

export interface SaldoExterno {
  idSaldoExterno: number;
  fechaSaldo: string;
  saldo: number;
  moneda: Moneda;
  fuente: FuenteSaldoExterno;
  referencia: string | null;
  nota: string | null;
  saldoCuentaALaFecha: number;
  diferencia: number;
  clasificacion: "cierra" | "menor-al-umbral" | "con-diferencia";
}

export interface NuevoSaldoExterno {
  fechaSaldo: string;
  saldo: number;
  moneda: Moneda;
  fuente: FuenteSaldoExterno;
  referencia?: string | null;
  nota?: string | null;
}

// ---- Archivos de comprobantes

export type EstadoArchivo =
  | "comprobante-legible-extension-incorrecta"
  | "no-legible"
  | "vacio"
  | "imagen-revisar";

export interface ArchivoIncompleto {
  ruta: string;
  periodo: string;
  proveedor: string;
  fecha: string | null;
  estado: EstadoArchivo;
  numero: string | null;
  importe: number | null;
  cargado: boolean;
  idCompra: number | null;
}

export interface ArchivosIncompletos {
  raiz: string;
  total: number;
  archivos: ArchivoIncompleto[];
}

// ---- Llamadas

export const revisionCuentasApi = {
  corte: () => apiGet<Corte>(`${BASE}/corte`),
  fijarCorte: (corte: string, motivo?: string) => apiPut<Corte>(`${BASE}/corte`, { corte, motivo }),

  tablero: (corte?: string) => apiGet<Tablero>(`${BASE}/tablero`, { corte }),
  fotos: (pagina = 1) => apiGet<{ total: number; fotos: FotoTablero[] }>(`${BASE}/tablero/fotos`, { pagina }),
  crearFoto: () => apiPost<FotoTablero>(`${BASE}/tablero/fotos`, {}),
  preguntas: () => apiGet<Pregunta[]>(`${BASE}/preguntas`),

  cola: (cola: Cola, pagina = 1, tamano = 100) => apiGet<ColaCuentas>(`${BASE}/colas/${cola}`, { pagina, tamano }),
  reglas: () => apiGet<ReglaLote[]>(`${BASE}/reglas`),
  simularLote: (cola: Cola, regla: string) => apiPost<Lote>(`${BASE}/lotes/simular`, { cola, regla }),
  tildarLote: (idCorreccion: number, cuerpo: { idsContacto: number[] } | { tildarTodas: true }) =>
    apiPut<Lote>(`${BASE}/lotes/${idCorreccion}/cuentas`, cuerpo),
  aplicarLote: (idCorreccion: number) => apiPost<Lote>(`${BASE}/lotes/${idCorreccion}/aplicar`, {}),
  revertirLote: (idCorreccion: number) => apiPost<Lote>(`${BASE}/lotes/${idCorreccion}/revertir`, {}),
  descartarLote: (idCorreccion: number) => apiDelete(`${BASE}/lotes/${idCorreccion}`),

  ficha: (idContacto: number) => apiGet<Ficha>(`${BASE}/cuentas/${idContacto}/ficha`),
  cambiarFicha: (idContacto: number, cambio: CambioFicha) => apiPut<Ficha>(`${BASE}/cuentas/${idContacto}/ficha`, cambio),
  confirmarInventario: (idContacto: number, fuentes: FuenteInventario[]) =>
    apiPut<Ficha>(`${BASE}/cuentas/${idContacto}/ficha/inventario`, { fuentes }),
  decisiones: (idContacto: number) => apiGet<Decision[]>(`${BASE}/cuentas/${idContacto}/decisiones`),
  registrarDecision: (idContacto: number, decision: { tipo: Decision["tipo"]; texto: string; evidencia?: string | null }) =>
    apiPost<Decision>(`${BASE}/cuentas/${idContacto}/decisiones`, decision),

  pagosSinFactura: (idContacto: number, opciones?: { desde?: string; incluirMarcados?: boolean }) =>
    apiGet<PagosSinFactura>(`${BASE}/cuentas/${idContacto}/pagos-sin-factura`, {
      desde: opciones?.desde,
      incluirMarcados: opciones?.incluirMarcados === undefined ? undefined : String(opciones.incluirMarcados),
    }),
  marcarPagoSinFactura: (idContacto: number, medio: string, idMovimiento: number, marca: MarcaPagoSinFactura) =>
    apiPut<PagoSinFactura>(`${BASE}/cuentas/${idContacto}/pagos-sin-factura/${medio}/${idMovimiento}`, marca),

  ventasDeCuenta: (idContacto: number) => apiGet<VentaDeCuenta[]>(`${BASE}/cuentas/${idContacto}/ventas`),
  saldosExternos: (idContacto: number) => apiGet<SaldoExterno[]>(`${BASE}/cuentas/${idContacto}/saldos-externos`),
  cargarSaldoExterno: (idContacto: number, saldo: NuevoSaldoExterno) =>
    apiPost<SaldoExterno>(`${BASE}/cuentas/${idContacto}/saldos-externos`, saldo),
  anularSaldoExterno: (idContacto: number, idSaldoExterno: number) =>
    apiDelete(`${BASE}/cuentas/${idContacto}/saldos-externos/${idSaldoExterno}`),

  archivosIncompletos: (opciones?: { periodo?: string; estado?: EstadoArchivo; pagina?: number }) =>
    apiGet<ArchivosIncompletos>(`${BASE}/archivos/incompletos`, {
      periodo: opciones?.periodo,
      estado: opciones?.estado,
      pagina: opciones?.pagina,
    }),
};
