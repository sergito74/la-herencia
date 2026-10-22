"""039 (FR-019, T033): SOLO LECTURA. Compara la valuación en kg de las cuentas de socios con el índice
actual (IndiceNovillo, haciinfo000013) y con el INMAG (IndiceINMAG, haciinfo000011), por socio:
- kg acumulados: los guardados (planilla / revisión 036) vs recalculados con INMAG a la fecha de cada movimiento;
- deuda actualizada de hoy: kg × índice de hoy, con cada índice.
No modifica nada; el cambio de índice se aplica solo con aprobación de Sergio.
Uso: python -m scripts.comparar_indice_socios_039
"""

import json
from bisect import bisect_right
from datetime import date, datetime
from pathlib import Path

from src.db.connection import fetch_all
from src.features.cuentas_socios.valuacion import INICIO_NOVILLO


def _serie(tabla: str) -> tuple[list[date], list[float]]:
    filas = fetch_all(f"SELECT Fecha f, CAST(Indice AS float) v FROM dbo.{tabla} WHERE Indice > 0 ORDER BY Fecha")
    return [date.fromisoformat(str(r["f"])[:10]) for r in filas], [r["v"] for r in filas]


def _a_fecha(serie, f: date) -> float | None:
    fechas, valores = serie
    i = bisect_right(fechas, f)
    return valores[i - 1] if i else None


def main() -> dict:
    viejo, inmag = _serie("IndiceNovillo"), _serie("IndiceINMAG")
    hoy = date.today()
    movs = fetch_all(
        "SELECT m.IdSocio s, m.Tipo t, CAST(m.Importe AS float) imp, m.Fecha f, CAST(ISNULL(m.ImporteKgCarne,0) AS float) kg "
        "FROM dbo.MovimientosCuentaSocio m WHERE ISNULL(m.Anulada,0)=0 AND ISNULL(m.ImporteKgCarne,0)<>0")
    socios = {}
    for m in movs:
        f = m["f"].date() if isinstance(m["f"], datetime) else date.fromisoformat(str(m["f"])[:10])
        signo = 1 if m["kg"] > 0 else -1
        x = socios.setdefault(m["s"], {"movimientos": 0, "kgGuardados": 0.0, "kgConInmag": 0.0, "sinInmag": 0})
        x["movimientos"] += 1
        x["kgGuardados"] += m["kg"]
        ind = _a_fecha(inmag, f) if f >= INICIO_NOVILLO else None
        if ind:
            x["kgConInmag"] += signo * abs(m["imp"]) * 0.5 / ind
        else:
            x["sinInmag"] += 1
            x["kgConInmag"] += m["kg"]
    hoy_viejo, hoy_inmag = _a_fecha(viejo, hoy), _a_fecha(inmag, hoy)
    for x in socios.values():
        x["kgGuardados"] = round(x["kgGuardados"], 3)
        x["kgConInmag"] = round(x["kgConInmag"], 3)
        x["difKg"] = round(x["kgConInmag"] - x["kgGuardados"], 3)
        x["pesosHoyIndiceActual"] = round(x["kgGuardados"] * hoy_viejo, 2)
        x["pesosHoyInmag"] = round(x["kgConInmag"] * hoy_inmag, 2)
        x["difPesosHoy"] = round(x["pesosHoyInmag"] - x["pesosHoyIndiceActual"], 2)
    out = {"fecha": hoy.isoformat(), "indiceActualHoy": hoy_viejo, "inmagHoy": hoy_inmag,
           "nota": "kgGuardados incluye filas migradas de la planilla Cajas Giamigli (kg de la planilla) y valuaciones 036.",
           "socios": socios}
    destino = Path(__file__).resolve().parents[2] / "backups" / "pastaje-039-schema"
    destino.mkdir(parents=True, exist_ok=True)
    (destino / f"comparacion-indice-socios-{hoy:%Y%m%d}.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    return out


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, default=str, ensure_ascii=False))
