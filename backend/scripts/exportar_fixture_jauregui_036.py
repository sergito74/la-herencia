"""036 (T009) — Exporta la cuenta de Jauregui y Morales tal como estaba antes del 09/10/2026 (solo lectura).

Guarda en `tests/fixtures/jauregui_antes.json` los movimientos de `vw_MovimientosCuenta_Base` del contacto 48 sin las
10 compras que se cargaron ese día (ids de compra 2143522625 a 2143522634): es el caso testigo del detector de pagos sin factura.

Uso (desde backend/): python -m scripts.exportar_fixture_jauregui_036
"""

from __future__ import annotations

import json
from pathlib import Path

from src.db.connection import fetch_all

ID_CONTACTO = 48
COMPRAS_CARGADAS_EL_09_10 = set(range(2143522625, 2143522635))
SALIDA = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "jauregui_antes.json"


def main() -> None:
    filas = fetch_all(
        "SELECT Fecha, Documento, [Nro Documento] AS nro, Deuda, Credito, Origen, IdOrigen "
        "FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ? ORDER BY Fecha, Origen, IdOrigen", (ID_CONTACTO,))
    movimientos = []
    for f in filas:
        if f["Origen"] == "Compras" and int(f["IdOrigen"]) in COMPRAS_CARGADAS_EL_09_10:
            continue
        movimientos.append({"fecha": f["Fecha"].date().isoformat(), "documento": f["Documento"], "nro": f["nro"],
                            "deuda": round(float(f["Deuda"] or 0), 2), "credito": round(float(f["Credito"] or 0), 2),
                            "origen": f["Origen"], "idOrigen": int(f["IdOrigen"])})
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps({"idContacto": ID_CONTACTO, "nota": "Sin las 10 compras cargadas el 09/10/2026",
                                  "movimientos": movimientos}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(movimientos)} movimientos guardados en {SALIDA}")


if __name__ == "__main__":
    main()
