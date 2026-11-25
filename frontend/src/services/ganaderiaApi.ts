import { apiGet, apiPost } from "@/services/apiClient";

export type VistaGanaderia = "ejercicio" | "campania";
export type MonedaGanaderia = "USD" | "ARS";

export interface FilaResultado {
  grupo: string;
  rubro: string;
  abreDetalle: boolean;
  valores: Record<string, number | null>;
}

export interface IndicadoresPeriodo {
  ventasNetas: number;
  ingresoNeto: number;
  margenBruto: number;
  estructura: number;
  resultadoOperativo: number;
  costoDirecto: number;
  haGanaderas: number;
  mbHa: number | null;
  costoDirectoHa: number | null;
  kgVendidos: number;
  cabezasVendidas: number;
  kgProducidos: number | null;
  kgHa?: number | null;
  costoPorKg: number | null;
  ev: number | null;
  evHa: number | null;
  sinInventario: boolean;
}

export interface ResultadoGanadero {
  vista: VistaGanaderia;
  moneda: MonedaGanaderia;
  conversion: string | null;
  periodos: { clave: string; desde: string; hasta: string; sinInventario: boolean }[];
  grupos: { grupo: string; titulo: string; signo: number }[];
  filas: FilaResultado[];
  indicadores: Record<string, IndicadoresPeriodo>;
  avisos: { periodo: string; texto: string }[];
  nota?: string | null;
}

export interface DetalleItem {
  fecha: string | null;
  documento: string | null;
  contacto: string | null;
  importe: number;
  enlace: string | null;
}

export const fetchResultadoGanadero = (vista: VistaGanaderia, moneda: MonedaGanaderia, desde: string, hasta: string,
  establecimiento?: number) =>
  apiGet<ResultadoGanadero>("/api/ganaderia/resultado", { vista, moneda, desde, hasta, establecimiento });

export const fetchDetalleGanadero = (grupo: string, rubro: string, periodo: string, vista: VistaGanaderia,
  establecimiento?: number) =>
  apiGet<{ items: DetalleItem[] }>("/api/ganaderia/resultado/detalle", { grupo, rubro, periodo, vista, establecimiento });

export const recalcularResultadoGanadero = () => apiPost<{ ok: boolean }>("/api/ganaderia/resultado/recalcular", {});

// ---------------------------------------------------------------- stock (US2)

export type DuenoFiltro = "todos" | "propia" | "terceros";

export interface FilaStock {
  idCategoria: number;
  categoria: string;
  cabezas: number;
  kg: number;
  kgEstimado: boolean;
  ev: number;
  dueno: "Propia" | "De terceros";
  duenoNombre: string | null;
  idEstablecimiento: number;
  establecimiento: string;
}

export interface StockHacienda {
  fecha: string;
  bases: { establecimiento: string; fecha: string; origen: string }[];
  categorias: FilaStock[];
  sinExplicar: { categoria: string; diferencia: number; establecimiento: string; dueno: string | null }[];
  totalCabezas: number;
  totalEv: number;
}

export interface MovimientoHacienda {
  id: number;
  fecha: string;
  tipo: string;
  categoriaNombre: string;
  categoriaDestinoNombre: string | null;
  cabezas: number;
  kg: number | null;
  kgEstimado: boolean;
  duenoNombre: string | null;
  establecimientoNombre: string;
  fuente: string;
  motivo: string | null;
  anulado: boolean;
  idVenta: number | null;
  enlace: string | null;
}

export interface MovimientoNuevo {
  fecha: string;
  tipo: string;
  categoria: number;
  categoriaDestino?: number | null;
  cabezas: number;
  kg?: number | null;
  dueno?: number | null;
  establecimiento: number;
  establecimientoDestino?: number | null;
  causa?: string | null;
  motivo?: string | null;
  confirmar?: boolean;
}

export const fetchStock = (fecha: string, establecimiento?: number, dueno: DuenoFiltro = "todos") =>
  apiGet<StockHacienda>("/api/ganaderia/stock", { fecha, establecimiento, dueno });

export const fetchMovimientos = (desde?: string, hasta?: string, tipo?: string, establecimiento?: number) =>
  apiGet<{ items: MovimientoHacienda[] }>("/api/ganaderia/movimientos", { desde, hasta, tipo, establecimiento });

export const fetchCategoriasHacienda = () => apiGet<{ items: { id: number; nombre: string }[] }>("/api/ganaderia/categorias");

export const registrarMovimiento = (m: MovimientoNuevo) => apiPost<{ id: number }>("/api/ganaderia/movimientos", m);

export const anularMovimiento = (id: number, motivo: string) =>
  apiPost<{ ok: boolean }>(`/api/ganaderia/movimientos/${id}/anular`, { motivo });

export const registrarRecuento = (r: {
  fecha: string; establecimiento: number; origen?: string; observaciones?: string | null;
  detalle: { categoria: number; dueno?: number | null; cabezas: number }[];
}) => apiPost<{ id: number; diferencias: { categoria: string; dueno: number | null; diferencia: number }[] }>(
  "/api/ganaderia/recuentos", r);
