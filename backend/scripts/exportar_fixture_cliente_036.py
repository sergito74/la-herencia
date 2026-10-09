"""036 (T009b) — Exporta una cuenta de cliente y una mixta como fixture del detector (solo lectura).

Guarda en `tests/fixtures/cliente_mixta.json` los movimientos de `vw_MovimientosCuenta_Base` de:
  * Ganaderos de Elordi (contacto 384): cliente puro, saldo cercano a cero.
  * Ferias del Centro (contacto 39): cuenta mixta (compras y ventas), 149 movimientos.
Sirven para validar la inversión de papeles del detector en clientes y mixtas (research D1).

Uso (desde backend/): python -m scripts.exportar_fixture_cliente_036
"""

from __future__ import annotations

import json
from pathlib import Path

from src.db.connection import fetch_all

CUENTAS = {"cliente": 384, "mixta": 39}
SALIDA = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "cliente_mixta.json"


def _movimientos(id_contacto: int) -> list[dict]:
    filas = fetch_all(
        "SELECT Fecha, Documento, [Nro Documento] AS nro, Deuda, Credito, Origen, IdOrigen "
        "FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ? ORDER BY Fecha, Origen, IdOrigen", (id_contacto,))
    return [{"fecha": f["Fecha"].date().isoformat(), "documento": f["Documento"], "nro": f["nro"],
             "deuda": round(float(f["Deuda"] or 0), 2), "credito": round(float(f["Credito"] or 0), 2),
             "origen": f["Origen"], "idOrigen": int(f["IdOrigen"])} for f in filas]


def main() -> None:
    datos = {tipo: {"idContacto": i, "movimientos": _movimientos(i)} for tipo, i in CUENTAS.items()}
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    for tipo, d in datos.items():
        print(f"{tipo}: contacto {d['idContacto']}, {len(d['movimientos'])} movimientos")
    print(f"Guardado en {SALIDA}")


if __name__ == "__main__":
    main()
