"use client";

export type Origen = "Insumo" | "Contratista";
export type EstadoPropuesta = "Pendiente" | "Aprobada" | "RequiereIntervencion";

export interface ContextoComercial {
  producto: string | null;
  idCompra: number | null;
  proveedor: string | null;
  tipoDocumento: string | null;
  numeroDocumento: string | null;
  fechaDocumento: string | null;
  monedaDocumento: string | null;
}

export interface PropuestaFraccion extends ContextoComercial {
  idPropuesta: number;
  idCorrida: string;
  origen: Origen;
  idDetalleCompra: number;
  idOrdenTrabajo: number | null;
  idLote: number | null;
  idCultivo: number | null;
  idCampania: number | null;
  idCentroCosto: number | null;
  esGanaderia: boolean | null;
  importe: number;
  cantidad: number | null;
  unidad: string | null;
  cultivo: string | null;
  campania: string | null;
  lote: string | null;
  centroCosto: string | null;
  estado: EstadoPropuesta;
  fechaCalculo: string;
  fechaAprobacion: string | null;
  usuarioAprobacion: string | null;
}

export interface CorreccionFraccion {
  idPropuesta: number;
  idLote?: number | null;
  idCultivo?: number | null;
  idCampania?: number | null;
  importe?: number | null;
}

export interface AprobarPropuestaIn {
  correcciones?: CorreccionFraccion[] | null;
}

export interface CostoCampaniaOut {
  totalPesos: number;
  totalDolares?: number | null;
}

export interface CostoNuevoCampaniaOut {
  totalPesos: number;
  totalAprobado: number;
  totalPendiente: number;
}

export interface ComparacionCampaniaOut {
  idCampania: number;
  campania: string | null;
  costoHeredado: CostoCampaniaOut;
  costoNuevo: CostoNuevoCampaniaOut;
  diferenciaPesos: number;
  diferenciaPorcentual: number | null;
  comparacionParcial: boolean;
}

export interface PendienteIntervencionOut extends ContextoComercial {
  idCorrida: string;
  origen: Origen;
  idDetalleCompra: number;
  motivo: "sinOrdenVinculada" | "repartoNoCierra" | "fueraDeCalendarioAgricola";
  fechaCalculo: string;
}

export interface AprobarLoteResultado {
  idCorrida: string;
  ok: boolean;
  error: string | null;
}

export interface AprobarLoteOut {
  resultados: AprobarLoteResultado[];
  aprobadas: number;
  fallidas: number;
}
