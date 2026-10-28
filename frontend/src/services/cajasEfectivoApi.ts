/** Cliente tipado de cajas 038; mantiene los campos numéricos de lectura 027. */

import { apiGet, apiPost, apiPut, apiPostForm } from "@/services/apiClient";

export type CajaSlug = "giamigli-sa" | "campo-chica" | "condominio-lsc" | "giamigli-dolares";

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
  idOperacion?: number | null;
  tipo?: string | null;
  anulada?: boolean;
  saldoCorridoDecimal?: string | null;
}

export interface SaldoCaja {
  caja: CajaSlug;
  saldo: number;
  ultimoArqueo?: ArqueoCaja | null;
}

export interface MovimientosCajaResponse {
  items: MovimientoCajaEfectivo[];
  page: number;
  pageSize: number;
  total: number;
  saldoAnteriorDecimal?: string;
  subtotalFiltradoDecimal?: string;
}

export function fetchSaldoCaja(caja: CajaSlug): Promise<SaldoCaja> {
  return apiGet<SaldoCaja>(`/api/cajas-efectivo/${caja}/saldo`, { detalleSaldo: "true" });
}

export function fetchMovimientosCaja(
  caja: CajaSlug,
  params: { page: number; pageSize: number; desde?: string; hasta?: string; tipo?: string; idContacto?: number; idSocio?: number; incluirAnuladas?: boolean }
): Promise<MovimientosCajaResponse> {
  return apiGet<MovimientosCajaResponse>(`/api/cajas-efectivo/${caja}/movimientos`, {
    ...params,
    incluirAnuladas: params.incluirAnuladas ? "true" : "false",
    detalleSaldo: "true",
  });
}

export const monedaCaja = (caja: string): "Pesos" | "Dolares" => caja === "giamigli-dolares" ? "Dolares" : "Pesos";

export const TIPOS_CAJA = {
  ingreso_dolares: "Entrada de dólares", egreso_dolares: "Salida de dólares",
  pago: "Pago a proveedor", cobro: "Cobro", aporte: "Aporte de socio",
  canje_socio: "Efectivo contra transferencia al socio",
  retiro_a_cuenta: "Retiro a cuenta / devolución de aporte", retiro_ganancias: "Retiro de ganancias",
  traspaso_cajas: "Traspaso entre cajas", extraccion_banco: "Extracción bancaria",
  deposito_banco: "Depósito bancario", gasto_sin_comprobante: "Gasto sin comprobante",
  retorno_sueldo_opcion_a: "Retorno de sueldo documentado (opción A)",
} as const;
export type TipoOperacionCaja = keyof typeof TIPOS_CAJA;
export interface OperacionCajaInput {
  tipo: TipoOperacionCaja; caja: CajaSlug; fecha: string; importe: string; concepto: string; cuenta: "A" | "B";
  idContacto?: number; idSocio?: number; cajaDestino?: CajaSlug; cajaContraparte?: CajaSlug;
  motivoRelacionGiamigli?: string; banco?: { medio: "bna" | "galicia" | "mercado-libre"; idMovimiento: number };
  intermediario?: string; evidencia?: string; idSalario?: number;
  compraParticular?: { idCompra: number; idSocio: number; idAsientoParticular?: number; confirmarAsientoNuevo?: boolean };
  aplicaciones?: { tipoDocumento: string; idDocumento: number; importeAplicado: string }[];
  repartos?: { idRubro: number; idCentroCostos: number; idDestino?: number; idCampania?: number; importePesos: string }[];
}
export interface PreviewCaja {
  previewVersion: string; advertencias: string[];
  efectosPrevistos: { caja: CajaSlug; importe: string; saldoResultante: string }[];
  contexto: { particular?: { importe: string; valuacion: { importeUSD: string; importeKgCarne: string } }; valuacion?: { importeUSD: string; importeKgCarne: string; dolar?: { valor: number | string; fecha: string }; novillo?: { valor: number | string; fecha: string } }; banco?: { cuentasExcluidas: { IdContacto: number; Origen: string; IdOrigen: number }[] } };
}
export interface ConfirmacionCaja { operacion: OperacionCajaInput; previewVersion: string; advertenciasAceptadas: string[] }
export interface DetalleOperacionCajaResponse {
  idOperacion: number; estado: "Vigente" | "Anulada"; version: number;
  operacion: OperacionCajaInput; usuario: string; fechaCarga: string;
  motivoAnulacion: string | null; usuarioAnulacion: string | null; fechaAnulacion: string | null;
  movimientos: { idMovimiento: number; caja: string; importeDecimal: string; anulada: boolean }[];
  efectos: { tipo: string; idRegistro: number; propio: boolean }[];
  anulacion?: { previewVersion?: string; advertencias?: string[]; bloqueo?: string; efectosPrevistos?: { caja: CajaSlug; saldoResultante: string }[] } | null;
}
export const previsualizarCaja = (op: OperacionCajaInput) => apiPost<PreviewCaja>("/api/cajas-efectivo/operaciones/previsualizar", op);
export const crearOperacionCaja = (body: ConfirmacionCaja, clave: string) => apiPost<DetalleOperacionCajaResponse>("/api/cajas-efectivo/operaciones", body, { "Idempotency-Key": clave });
export const detalleOperacionCaja = (id: number) => apiGet<DetalleOperacionCajaResponse>(`/api/cajas-efectivo/operaciones/${id}`);
export const anularOperacionCaja = (id: number, motivo: string, versionEsperada: number, previewVersion?: string, advertenciasAceptadas: string[] = []) => apiPost<DetalleOperacionCajaResponse>(`/api/cajas-efectivo/operaciones/${id}/anular`, { motivo, versionEsperada, previewVersion, advertenciasAceptadas });

export interface ArqueoCaja {
  idArqueo: number; caja: CajaSlug; fechaCorte: string; secuenciaCorte: number; version: number;
  estado: "Borrador" | "Confirmado" | "Invalidado" | "Desactualizado";
  saldoSistema: string; totalContado: string; diferencia: string; previewVersion: string;
  saldoRecalculadoDecimal: string; diferenciaVigenteDecimal: string; idOperacionAjuste: number | null;
  idArqueoAnterior: number | null; usuario: string; usuarioConfirmacion: string | null;
  denominaciones: { valor: string; cantidad: number }[];
  advertencias?: string[];
}
export interface RecuentoInput { fechaCorte: string; denominaciones: { valor: string; cantidad: number }[]; versionEsperada?: number; idArqueoAnterior?: number }
export const listarArqueosCaja = (caja: CajaSlug, page = 1) => apiGet<{ items: ArqueoCaja[]; total: number; page: number; pageSize: number }>(`/api/cajas-efectivo/${caja}/arqueos`, { page });
export const guardarArqueoCaja = (caja: CajaSlug, body: RecuentoInput, id?: number) => id ? apiPut<ArqueoCaja>(`/api/cajas-efectivo/${caja}/arqueos/${id}`, body) : apiPost<ArqueoCaja>(`/api/cajas-efectivo/${caja}/arqueos`, body);
export const confirmarArqueoCaja = (a: ArqueoCaja, aceptarDiferencia: boolean, advertenciasAceptadas: string[]) => apiPost<ArqueoCaja>(`/api/cajas-efectivo/${a.caja}/arqueos/${a.idArqueo}/confirmar`, { versionEsperada: a.version, previewVersion: a.previewVersion, aceptarDiferencia, advertenciasAceptadas });

export interface FilaImportacionCaja {
  idFila: number; hoja: string; fila: number; estado: string; motivo: string | null;
  datos: { caja: CajaSlug; fecha: string | null; importe: string | null; concepto: string; cuenta: string };
  idMovimiento: number | null; idOperacion: number | null;
  diferenciasVinculo?: string[];
  candidatas: { idMovimiento: number; idOperacion: number | null; concepto: string; anulada: boolean }[];
}
export interface LoteCaja {
  idLote: number; estado: string; libro: string; fechaCorte: string; filas: FilaImportacionCaja[];
  comparacion: Partial<Record<CajaSlug, { saldoSistema: string; saldoPlanilla: string | null; diferencia: string | null; pendientes: number; cobertura: string; soloSistema: number[]; ambiguas: number[]; modificadas: number[]; excluidas: number[] }>>;
}
export interface DecisionImportacionCaja {
  idFila: number; accion: "importar" | "vincular" | "excluir" | "pendiente";
  idMovimiento?: number; motivo?: string; operacion?: ConfirmacionCaja; confirmarDistinto?: boolean;
}
export const previewImportacionCaja = (archivo: File, libro: string, fechaCorte: string) => {
  const form = new FormData(); form.append("archivo", archivo); form.append("libro", libro); form.append("fechaCorte", fechaCorte);
  return apiPostForm<LoteCaja>("/api/cajas-efectivo/importaciones/previsualizar", form);
};
export const confirmarImportacionCaja = (id: number, resoluciones: DecisionImportacionCaja[], aceptarSaldoNegativoLote = false) => apiPost<LoteCaja>(`/api/cajas-efectivo/importaciones/${id}/confirmar`, { resoluciones, aceptarSaldoNegativoLote });
