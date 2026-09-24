import { strict as assert } from "node:assert";
import { agruparImputacion, cantidadFormateada, etiquetaDestino, type FilaResumen } from "./agrupacionImputacion";

const base: FilaResumen = {
  idPropuesta: 1, idCultivo: 1, idCampania: 2, idCentroCosto: null, idLote: 3,
  cultivo: "Soja", campania: "2026/27", centroCosto: null, lote: "Norte",
  esGanaderia: false, estado: "Pendiente", importe: 100, cantidad: 2.5,
  unidad: "L", producto: "Herbicida", idDetalleCompra: 10, origen: "Insumo", idOrdenTrabajo: 4,
};

const grupos = agruparImputacion([
  base,
  { ...base, idPropuesta: 2, idLote: 5, cantidad: 1.5, importe: 60 },
  { ...base, idPropuesta: 3, idDetalleCompra: 11 },
  { ...base, idPropuesta: 4, unidad: "kg" },
  { ...base, idPropuesta: 5, idCampania: 3 },
  { ...base, idPropuesta: 6, estado: "RequiereIntervencion", idCultivo: null, idOrdenTrabajo: null },
  { ...base, idPropuesta: 7, idCultivo: null, idOrdenTrabajo: null },
]);
assert.equal(grupos.length, 4);
assert.equal(grupos[0].importe, 360);
assert.equal(grupos[0].cantidades.length, 3);
assert.equal(grupos[0].cantidades[0].cantidad, 4);
assert.equal(grupos[0].filas.length, 4);
assert.equal(grupos[2].destino, "Requiere intervención");
assert.equal(grupos[3].destino, "En stock sin consumir");
assert.equal(agruparImputacion([base, { ...base, cantidad: null }])[0].cantidades[0].cantidad, null);
assert.equal(cantidadFormateada({ ...base, cantidad: 0 }), "0 L");
assert.equal(cantidadFormateada({ ...base, cantidad: null }), "No registrada");
assert.equal(cantidadFormateada({ ...base, origen: "Contratista", cantidad: null }), "No aplica");
assert.equal(etiquetaDestino({ ...base, idCultivo: null, idCentroCosto: 7, centroCosto: "Administración" }), "Administración");
assert.equal(etiquetaDestino({ ...base, idCultivo: null, esGanaderia: true }), "Ganadería");
assert.deepEqual(agruparImputacion([]), []);
console.log("Resumen de imputación: agrupación, cantidades y destinos verificados.");

