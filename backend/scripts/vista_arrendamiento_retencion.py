"""Vista de saldos: los arrendamientos descuentan la retención de Ganancias sufrida (035, 2026-10-08).

La rama `Contrato Arrendamiento` de `vw_MovimientosCuenta_Base` tomaba `Importe total del contrato` como crédito sin
descontar `Retencion Ganancias`, que sí se descuenta en las ventas de hacienda. Hallado en Fideicomiso La Esperanza (562):
el arrendatario retuvo Ganancias en cada cuota (certificados SICORE 0000-2024-000026, 0000-2024-000037 y 0000-2025-000032)
y el saldo quedaba inflado en $1.168.815,90. Los contratos anteriores tienen la retención en 0, no cambian.
Autorización de Sergio el 2026-10-08.

Uso: `python -m scripts.vista_arrendamiento_retencion --simular` muestra el efecto; sin argumentos aplica
(respaldo verificado, definición anterior en `scripts/vista_base_anterior_arrendamiento_20261008.sql`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all

VIEJO = "    a.[Importe total del contrato] AS Credito,"
NUEVO = "    a.[Importe total del contrato] - ISNULL(a.[Retencion Ganancias], 0) AS Credito,"
RESPALDO_DEFINICION = Path(__file__).with_name("vista_base_anterior_arrendamiento_20261008.sql")


def _saldos(vista: str = "vw_MovimientosCuenta_Base") -> dict[int, float]:
    return {r["k"]: float(r["s"]) for r in fetch_all(
        f"SELECT IdContacto AS k, SUM(Credito - Deuda) AS s FROM dbo.{vista} GROUP BY IdContacto")}


def _comparar(antes: dict[int, float], despues: dict[int, float]) -> None:
    nombres = {r["id"]: r["rs"] for r in fetch_all("SELECT IdContacto id, [Razon Social] rs FROM dbo.Contactos")}
    cambios = sorted(((k, despues.get(k, 0) - antes.get(k, 0)) for k in set(antes) | set(despues)), key=lambda t: -abs(t[1]))
    cambios = [c for c in cambios if abs(c[1]) > 0.005]
    print(f"Cuentas cuyo saldo cambia: {len(cambios)}")
    for k, d in cambios:
        print(f"  {k:5} {str(nombres.get(k))[:34]:34} antes {antes.get(k, 0):>15,.2f}  después {despues.get(k, 0):>15,.2f}  ({d:>+14,.2f})")


def main(solo_simular: bool) -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo sobre WC")
        definicion = cur.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_MovimientosCuenta_Base'))").fetchone()[0].replace("\r\n", "\n")
        if NUEVO in definicion:
            print("La vista ya descuenta la retención en los arrendamientos.")
            return
        if definicion.count(VIEJO) != 1:
            raise RuntimeError("No se encontró la rama de arrendamientos con el formato esperado.")
        antes = _saldos()
        nueva = definicion.replace(VIEJO, NUEVO)
        if solo_simular:
            temporal = nueva.replace("CREATE VIEW dbo.vw_MovimientosCuenta_Base", "CREATE VIEW dbo.vw_MovimientosCuenta_Base_sim", 1)
            if temporal == nueva:
                raise RuntimeError("No se pudo armar la vista temporal.")
            cur.execute(temporal)
            try:
                despues = _saldos("vw_MovimientosCuenta_Base_sim")
            finally:
                cur.execute("DROP VIEW dbo.vw_MovimientosCuenta_Base_sim")
            _comparar(antes, despues)
            return
        from src.features.vinculos.backup import backup_verificado

        print(f"Respaldo verificado: {backup_verificado('vista-arrendamiento-retencion')}")
        RESPALDO_DEFINICION.write_text(definicion, encoding="utf-8")
        cur.execute(nueva.replace("CREATE VIEW", "ALTER VIEW", 1))
        _comparar(antes, _saldos())
    finally:
        conn.close()


if __name__ == "__main__":
    main("--simular" in sys.argv)
