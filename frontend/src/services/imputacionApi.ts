"use client";

export type Origen = "Insumo" | "Contratista";
export type EstadoPropuesta = "Pendiente" | "Aprobada" | "RequiereIntervencion";

export interface PropuestaFraccion {
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
  estado: EstadoPropuesta;
  fechaCalculo: string;
  fechaAprobacion: string | null;
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

export interface PendienteIntervencionOut {
  idCorrida: string;
  origen: Origen;
  idDetalleCompra: number;
  motivo: "sinOrdenVinculada" | "repartoNoCierra";
  fechaCalculo: string;
}
