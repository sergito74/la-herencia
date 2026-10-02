import { apiGet, apiPatch, apiPost } from "@/services/apiClient";

// 032 — Recálculo FIFO de cuentas corrientes (specs/032-recalculo-fifo-cuentas/contracts/api.md)

export type Alcance = "etapa-1" | "todos" | number[];
export type FiltroContactos = "todos" | "cierra" | "no-cierra" | "mejora" | "empeora" | "excepcion";
export type Tendencia = "igual" | "mejora" | "empeora";

export interface ResumenEjecucion {
  contactos: number;
  cierranDespues: number;
  cerrabanAntes: number;
  mejoran: number;
  empeoran: number;
  excepciones: number;
  aplicaciones: number;
  segundos: number | null;
}

export interface Ejecucion {
  idEjecucion: number;
  tipo: "simulacion" | "aplicacion" | "continua";
  estado: "simulada" | "aplicada" | "revertida" | "descartada";
  alcance: Alcance;
  fechaInicio: string;
  fechaFin: string | null;
  usuario: string;
  backupArchivo: string | null;
  resumen: ResumenEjecucion | null;
}

export interface CodigoDescripcion {
  codigo: string;
  descripcion: string;
}

export interface ContactoEjecucion {
  idContacto: number;
  nombre: string;
  moneda: "ARS" | "USD";
  facturadoAntes: number;
  pagadoAntes: number;
  aplicadoAntes: number;
  aplicadoDespues: number;
  anticipoAbierto: number;
  saldo: number;
  volumen: number;
  cerrabaAntes: boolean;
  cierraDespues: boolean;
  tendencia: Tendencia;
  controles: CodigoDescripcion[];
  marcas: CodigoDescripcion[];
  estadoExcepcion: "ninguna" | "pendiente" | "resuelta";
  notaExcepcion: string | null;
}

export interface PaginaContactos {
  items: ContactoEjecucion[];
  total: number;
  pagina: number;
  tamanio: number;
}

export interface RenglonCuenta {
  origen: string;
  id: number;
  cuota: number | null;
  lado: "D" | "C";
  clase: "doc" | "dinero";
  documento: string | null;
  nro: string;
  fecha: string;
  vencimiento: string;
  moneda: "ARS" | "USD";
  importe: number;
  aplicado: number;
  suspendido: boolean;
  saldoAcumuladoArs: number;
}

export interface AplicacionPropuesta {
  credito: { origen: string; id: number };
  debito: { origen: string; id: number; cuota: number | null };
  importeAplicado: number;
  moneda: "ARS" | "USD";
  importeArs: number;
  tipoCambio: number | null;
  diferenciaCambio: number;
  regla: string;
  fechaCredito: string | null;
  fechaVencimiento: string | null;
}

export interface DetalleContacto {
  contacto: ContactoEjecucion;
  renglones: RenglonCuenta[];
  aplicaciones: AplicacionPropuesta[];
}

const BASE = "/api/recalculo-fifo";

export function fetchEjecuciones(): Promise<Ejecucion[]> {
  return apiGet<Ejecucion[]>(`${BASE}/ejecuciones`);
}

export function simular(alcance: Alcance): Promise<{ idEjecucion: number; resumen: ResumenEjecucion }> {
  return apiPost(`${BASE}/ejecuciones`, { alcance });
}

export function descartarEjecucion(idEjecucion: number): Promise<void> {
  return apiPost(`${BASE}/ejecuciones/${idEjecucion}/descartar`, {});
}

export function fetchContactos(
  idEjecucion: number,
  filtro: FiltroContactos,
  pagina: number,
  tamanio = 50
): Promise<PaginaContactos> {
  return apiGet<PaginaContactos>(`${BASE}/ejecuciones/${idEjecucion}/contactos`, { filtro, pagina, tamanio, orden: "volumen" });
}

export function fetchDetalleContacto(idEjecucion: number, idContacto: number): Promise<DetalleContacto> {
  return apiGet<DetalleContacto>(`${BASE}/ejecuciones/${idEjecucion}/contactos/${idContacto}`);
}

export function marcarExcepcion(
  idEjecucion: number,
  idContacto: number,
  estado: "pendiente" | "resuelta",
  nota: string | null
): Promise<void> {
  return apiPatch(`${BASE}/ejecuciones/${idEjecucion}/contactos/${idContacto}/excepcion`, { estado, nota });
}

export interface ResultadoAplicar {
  aplicados: number[];
  sinCambios: number[];
  omitidos: number[];
  backup: string;
}

export function aplicarEjecucion(
  idEjecucion: number,
  contactos: number[] | null,
  confirmarEmpeoran = false
): Promise<ResultadoAplicar> {
  return apiPost(`${BASE}/ejecuciones/${idEjecucion}/aplicar`, { contactos, confirmarEmpeoran });
}

export function revertirEjecucion(idEjecucion: number): Promise<{ idEjecucion: number; estado: string }> {
  return apiPost(`${BASE}/ejecuciones/${idEjecucion}/revertir`, {});
}
