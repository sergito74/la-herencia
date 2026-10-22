/** Cliente tipado de contratos de pastaje (039). Importes Decimal como string (contracts/api.md). */

import { apiGet, apiPost, apiPut } from "@/services/apiClient";

export type TipoTarifa = "kg_novillo" | "fijo_ars" | "fijo_usd";
export type TipoMovimiento = "ingreso" | "egreso" | "muerte" | "faltante" | "nacimiento" | "destete" | "recuento";

export interface Tarifa {
  id?: number;
  idTipoHacienda: number;
  tipoTarifa: TipoTarifa;
  valor: string;
  vigenteDesde: string | null;
}
export interface MesResumen {
  periodo: string;
  devengado: string | null;
  liquidado: string | null;
  facturado: string;
  cobrado: string;
  saldo: string;
  estado: string;
  diferencia: string | null;
  alertas: string[];
  idLiquidacion: number | null;
}
export interface Contrato {
  id: number;
  idContacto: number;
  cliente: string;
  cuit: string | null;
  establecimiento: string | null;
  fechaInicio: string;
  fechaFin: string | null;
  modalidad: string;
  condicionVenta: string;
  alicuotaIva: string;
  carpetaDocumentos: string | null;
  archivoContrato: string | null;
  clausulaInfraestructura: string | null;
  clausulaSanidad: string | null;
  clausulaMortandad: string | null;
  otrasClausulas: string | null;
  estado: "vigente" | "finalizado" | "anulado";
  motivoEstado: string | null;
  version: number;
  tarifas: Tarifa[];
}
export interface ContratoFicha extends Contrato {
  meses: MesResumen[];
}
export interface TarjetaContrato extends Contrato {
  cabezasActuales: { categoria: string; cabezas: number }[];
  inmagUltimo: { fecha: string; indice: string } | null;
  promedioMesCurso: string | null;
  estimadoMesCurso: string | null;
  proximoPaso: string | null;
  alertas: string[];
}
export interface ContratoInput {
  idContacto: number;
  fechaInicio: string;
  fechaFin?: string | null;
  carpetaDocumentos?: string | null;
  archivoContrato?: string | null;
  clausulaInfraestructura?: string | null;
  clausulaSanidad?: string | null;
  clausulaMortandad?: string | null;
  otrasClausulas?: string | null;
}
export interface Movimiento {
  id: number;
  fecha: string;
  tipo: TipoMovimiento;
  idTipoHacienda: number;
  categoria: string;
  cabezas: number;
  cabezasSistema: number | null;
  numeroDte: string | null;
  observacion: string | null;
  estado: "vigente" | "anulado";
  motivoAnulacion: string | null;
  creadoPor: string;
  version: number;
}
export interface Bitacora {
  movimientos: Movimiento[];
  cabezasActuales: { idTipoHacienda: number; categoria: string; cabezas: number }[];
}
export interface Tramo {
  idTipoHacienda: number;
  categoria: string;
  desde: string;
  hasta: string;
  cabezas: number;
  dias: number;
  tipoTarifa: TipoTarifa;
  valorMes: string;
  kg: string;
  importe: string;
}
export interface Liquidacion {
  id: number;
  idContrato: number;
  periodo: string;
  tipo: "mensual" | "ajuste";
  idLiquidacionOriginal: number | null;
  estado: "borrador" | "confirmada" | "anulada";
  precioPromedio: string | null;
  kg: string;
  neto: string;
  iva: string;
  total: string;
  moneda: string;
  archivoPdf: string | null;
  confirmadaPor: string | null;
  version: number;
  tramos?: Tramo[];
  indices?: { fecha: string; indice: string }[];
}
export interface Preview {
  periodo: string;
  bloqueo: string | null;
  precioPromedio?: string | null;
  kg?: string;
  neto?: string;
  iva?: string;
  total?: string;
  diasMes?: number;
  tramos: Tramo[];
  indices: { fecha: string; indice: string }[];
  textoFactura: string[];
  liquidacion: Liquidacion | null;
}
export interface Comprobante {
  id: number;
  idContrato: number;
  idLiquidacion: number | null;
  tipo: "factura" | "nota_debito" | "nota_credito";
  letra: string;
  puntoVenta: number;
  numero: number;
  fecha: string;
  vtoPago: string | null;
  cae: string | null;
  vtoCae: string | null;
  cuitCliente: string | null;
  periodoDesde: string | null;
  periodoHasta: string | null;
  detalle: string | null;
  neto: string;
  iva: string;
  total: string;
  idComprobanteAsociado: number | null;
  archivoPdf: string | null;
  estado: "vigente" | "anulado";
  version: number;
  cobrado: string;
  saldo: string;
}
export interface ComprobanteLeido {
  tipo: Comprobante["tipo"];
  letra: string;
  puntoVenta: number;
  numero: number;
  fecha: string;
  vtoPago: string | null;
  cae: string | null;
  vtoCae: string | null;
  cuitCliente: string | null;
  periodoDesde: string | null;
  periodoHasta: string | null;
  detalle: string | null;
  neto: string;
  iva: string;
  total: string;
  otrosTributos: string;
  cuitEmisor: string;
  cliente: string | null;
  advertencias: string[];
  archivoPdf: string;
}
export interface ComprobanteInput extends Omit<ComprobanteLeido, "cuitEmisor" | "cliente" | "advertencias"> {
  idContrato: number;
  idLiquidacion: number | null;
  idComprobanteAsociado: number | null;
  aceptarAdvertencias: boolean;
}
export interface IndiceDia {
  fecha: string;
  indice: string;
  cabIngresadas: number | null;
  origen: "auto" | "manual";
  nota: string | null;
}

const B = "/api/pastaje";

export const listarContratos = (estado?: string) => apiGet<TarjetaContrato[]>(`${B}/contratos`, { estado });
export const fichaContrato = (id: number) => apiGet<ContratoFicha>(`${B}/contratos/${id}`);
export const crearContrato = (body: ContratoInput & { tarifas: Tarifa[] }) => apiPost<ContratoFicha>(`${B}/contratos`, body);
export const actualizarContrato = (id: number, body: ContratoInput & { tarifasNuevas: Tarifa[]; version: number }) =>
  apiPut<ContratoFicha>(`${B}/contratos/${id}`, body);
export const finalizarContrato = (id: number, fechaFin: string, motivo: string, version: number) =>
  apiPost<ContratoFicha>(`${B}/contratos/${id}/finalizar`, { fechaFin, motivo, version });
export const anularContrato = (id: number, motivo: string, version: number) =>
  apiPost<ContratoFicha>(`${B}/contratos/${id}/anular`, { motivo, version });

export const obtenerBitacora = (id: number) => apiGet<Bitacora>(`${B}/contratos/${id}/bitacora`);
export const registrarMovimiento = (
  id: number,
  body: { fecha: string; tipo: TipoMovimiento; idTipoHacienda: number; cabezas: number; numeroDte?: string; observacion?: string }
) =>
  apiPost<{ id: number; cabezasSistema: number | null; diferencia: number | null; afectaLiquidado: boolean }>(
    `${B}/contratos/${id}/bitacora`,
    body
  );
export const anularMovimiento = (id: number, motivo: string, version: number) =>
  apiPost<{ id: number; afectaLiquidado: boolean }>(`${B}/bitacora/${id}/anular`, { motivo, version });

export const previewLiquidacion = (id: number, periodo: string) =>
  apiGet<Preview>(`${B}/contratos/${id}/liquidaciones/preview`, { periodo });
export const listarLiquidaciones = (id: number) => apiGet<Liquidacion[]>(`${B}/contratos/${id}/liquidaciones`);
export const crearLiquidacion = (id: number, periodo: string) => apiPost<Liquidacion>(`${B}/contratos/${id}/liquidaciones`, { periodo });
export const confirmarLiquidacion = (l: Liquidacion) => apiPost<Liquidacion>(`${B}/liquidaciones/${l.id}/confirmar`, { version: l.version });
export const anularLiquidacion = (l: Liquidacion) => apiPost<Liquidacion>(`${B}/liquidaciones/${l.id}/anular`, { version: l.version });
export const crearAjuste = (idLiq: number) => apiPost<Liquidacion>(`${B}/liquidaciones/${idLiq}/ajuste`, {});
export const textoFactura = (idLiq: number) =>
  apiGet<{ detalle: string[]; neto: string; iva: string; total: string }>(`${B}/liquidaciones/${idLiq}/texto-factura`);
export const urlPdfLiquidacion = (idLiq: number) => `${B}/liquidaciones/${idLiq}/pdf`;

export const leerComprobante = (ruta: string) => apiPost<ComprobanteLeido>(`${B}/comprobantes/leer`, { ruta });
export const registrarComprobante = (body: ComprobanteInput) => apiPost<Comprobante>(`${B}/comprobantes`, body);
export const listarComprobantes = (id: number) => apiGet<Comprobante[]>(`${B}/contratos/${id}/comprobantes`);
export const anularComprobante = (c: Comprobante, motivo: string) =>
  apiPost<Comprobante>(`${B}/comprobantes/${c.id}/anular`, { motivo, version: c.version });
export const urlPdfComprobante = (id: number) => `${B}/comprobantes/${id}/pdf`;

export const indiceInmag = (desde: string, hasta: string) => apiGet<IndiceDia[]>(`${B}/indice-inmag`, { desde, hasta });
export const actualizarInmag = () => apiPost<{ agregados: number; sinIndice: string[] }>(`${B}/indice-inmag/actualizar`, {});
export const cargarInmagManual = (fecha: string, indice: string, nota: string) =>
  apiPut<{ fecha: string; indice: string }>(`${B}/indice-inmag/${fecha}`, { indice, nota });
export const ingresosPastaje = (campania: string) =>
  apiGet<{ establecimiento: string; neto: string }[]>(`${B}/ingresos`, { campania });
export const categoriasHacienda = () => apiGet<{ id: number; nombre: string }[]>(`${B}/categorias`);
