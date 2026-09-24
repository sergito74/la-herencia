export interface FilaResumen {
  idPropuesta: number;
  idCultivo: number | null;
  idCampania: number | null;
  idCentroCosto: number | null;
  idLote: number | null;
  cultivo: string | null;
  campania: string | null;
  centroCosto: string | null;
  lote: string | null;
  esGanaderia: boolean | null;
  estado: string;
  importe: number;
  cantidad: number | null;
  unidad: string | null;
  producto: string;
  idDetalleCompra: number;
  origen: "Insumo" | "Contratista";
  idOrdenTrabajo: number | null;
}

export function etiquetaDestino(fila: Pick<FilaResumen, "estado" | "idCultivo" | "cultivo" | "campania" | "idCentroCosto" | "centroCosto" | "esGanaderia" | "idOrdenTrabajo" | "origen">): string {
  if (fila.estado === "RequiereIntervencion") return "Requiere intervención";
  if (fila.idCultivo != null) return `${fila.cultivo || "Cultivo sin nombre"} / ${fila.campania || "Campaña no registrada"}`;
  if (fila.idCentroCosto != null) return fila.centroCosto || "Centro de costos sin nombre";
  if (fila.esGanaderia) return "Ganadería";
  if (fila.origen === "Insumo" && fila.idOrdenTrabajo == null) return "En stock sin consumir";
  return "Destino no registrado";
}

export function cantidadFormateada(fila: Pick<FilaResumen, "cantidad" | "unidad" | "origen">): string {
  if (fila.cantidad == null) return fila.origen === "Contratista" ? "No aplica" : "No registrada";
  return `${fila.cantidad.toLocaleString("es-AR", { maximumFractionDigits: 6 })} ${fila.unidad || "(unidad no registrada)"}`;
}

interface CantidadResumen {
  clave: string;
  producto: string;
  origen: FilaResumen["origen"];
  cantidad: number | null;
  unidad: string | null;
}

export interface GrupoResumen {
  clave: string;
  destino: string;
  importe: number;
  cantidades: CantidadResumen[];
  filas: FilaResumen[];
}

export function agruparImputacion(filas: FilaResumen[]): GrupoResumen[] {
  const grupos = new Map<string, GrupoResumen>();
  for (const fila of filas) {
    const clave = fila.estado === "RequiereIntervencion"
      ? "intervencion"
      : fila.idCultivo != null
        ? `cultivo:${fila.idCultivo}:${fila.idCampania}`
        : fila.idCentroCosto != null
          ? `centro:${fila.idCentroCosto}`
          : fila.esGanaderia ? "ganaderia" : etiquetaDestino(fila);
    let grupo = grupos.get(clave);
    if (!grupo) {
      grupo = { clave, destino: etiquetaDestino(fila), importe: 0, cantidades: [], filas: [] };
      grupos.set(clave, grupo);
    }
    grupo.importe += Number(fila.importe);
    grupo.filas.push(fila);
    const claveCantidad = JSON.stringify([fila.origen, fila.idDetalleCompra, fila.producto, fila.unidad]);
    const cantidad = grupo.cantidades.find((item) => item.clave === claveCantidad);
    if (cantidad) {
      // Una fracción sin cantidad impide presentar un total físico completo.
      cantidad.cantidad = cantidad.cantidad == null || fila.cantidad == null ? null : cantidad.cantidad + Number(fila.cantidad);
    } else {
      grupo.cantidades.push({ clave: claveCantidad, producto: fila.producto, origen: fila.origen, cantidad: fila.cantidad, unidad: fila.unidad });
    }
  }
  return Array.from(grupos.values());
}
