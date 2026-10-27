import type { CompraDetalleCompleto, fetchCompraDetalle } from "@/services/comprasApi";

/**
 * `GET /api/compras/{id}` (002-compras, ampliado en 006) devuelve el
 * detalle de solo lectura con la forma `CompraDetalle`; `CompraForm`
 * espera `CompraDetalleCompleto` (el contrato de alta/edición, con
 * `subtotalNeto`/`ivaCabecera`/`importeTotal`/`pesificado`/`warnings`).
 * Como el detalle de lectura no calcula esos totales, se recalculan acá
 * mismo en el cliente solo para el prefill visual — el guardado real
 * (`PUT`) siempre recalcula en el backend a partir de las líneas.
 */
export function compraDetalleAInput(
  data: Awaited<ReturnType<typeof fetchCompraDetalle>>,
  idCompra: number
): CompraDetalleCompleto {
  const lineas = data.lineas.map((l) => ({
    productoServicio: l.productoServicio ?? "",
    cantidad: l.cantidad ?? 0,
    precioUnitario: l.precioUnitario ?? 0,
    iva: l.iva ?? 0,
    unidad: null,
    idCentroCosto: l.imputacion?.idCentroCosto ?? null,
    idDestino: l.imputacion?.idDestino ?? null,
    idRubro: l.imputacion?.idRubro ?? null,
    campaña: l.imputacion?.campania ?? null,
    ajusteFinanciero: false,
    idDetalleCompra: l.idDetalleCompra,
    subtotal: (l.cantidad ?? 0) * (l.precioUnitario ?? 0),
    importeIva: ((l.cantidad ?? 0) * (l.precioUnitario ?? 0) * (l.iva ?? 0)) / 100,
  }));

  const subtotalNeto = lineas.reduce((acc, l) => acc + l.subtotal, 0);
  const ivaCabecera = lineas.reduce((acc, l) => acc + l.importeIva, 0);

  return {
    idCompra,
    idContacto: data.proveedor?.idContacto ?? 0,
    fecha: data.fecha ?? "",
    tipo: (data.tipo as CompraDetalleCompleto["tipo"]) ?? "A",
    tipoDocumento: (data.tipoDocumento as CompraDetalleCompleto["tipoDocumento"]) ?? "Factura",
    numeroDocumento: data.numeroDocumento ?? "",
    moneda: (data.moneda as CompraDetalleCompleto["moneda"]) ?? "Pesos",
    tipoDeCambio: data.tipoDeCambio ?? null,
    ingresosBrutos: data.ingresosBrutos ?? 0,
    percepcionIva: data.percepcionIva ?? 0,
    conceptosNoGravados: data.conceptosNoGravados ?? 0,
    guias: data.guias ?? 0,
    comision: data.comision ?? 0,
    financiacion: data.financiacion ?? 0,
    gastosVarios: data.gastosVarios ?? 0,
    leyDeSellos: data.leyDeSellos ?? 0,
    resGral4169: data.resGral4169 ?? 0,
    ajustaTipoCambio: data.ajustaTipoCambio ?? false,
    documentoOriginal: data.documentoOriginal ?? null,
    lineas,
    vencimientos: data.vencimientos.map((v) => ({
      idVencimiento: v.idVencimiento,
      fechaVencimiento: v.fechaVencimiento ?? "",
    })),
    subtotalNeto,
    ivaCabecera,
    importeTotal: subtotalNeto + ivaCabecera,
    pesificado: null,
    warnings: [],
  };
}
