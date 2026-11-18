import { strict as assert } from "node:assert";
import { atajos, etiquetaRango } from "./RangoFechas";

// 18/11/2026: la campaña empieza el 1 de julio.
const nov = new Date(2026, 10, 18);
const a = Object.fromEntries(atajos(nov).map((x) => [x.id, x.rango]));
assert.deepEqual(a["campania"], { desde: "2026-07-01", hasta: "2027-06-30" });
assert.deepEqual(a["campania-anterior"], { desde: "2025-07-01", hasta: "2026-06-30" });
assert.deepEqual(a["mes-pasado"], { desde: "2026-10-01", hasta: "2026-10-31" });
assert.deepEqual(a["mes"], { desde: "2026-11-01", hasta: "2026-11-30" });
const marzo = new Date(2027, 2, 5);
assert.equal(atajos(marzo).find((x) => x.id === "campania")?.label, "Campaña 2026/2027");
assert.equal(etiquetaRango({ desde: "", hasta: "" }), "Todas las fechas");
assert.equal(etiquetaRango({ desde: "2026-07-01", hasta: "2027-06-30" }, nov), "Campaña 2026/2027");
assert.equal(etiquetaRango({ desde: "2026-03-02", hasta: "2026-04-15" }, nov), "02/03/2026 – 15/04/2026");
console.log("rangoFechas ok");
