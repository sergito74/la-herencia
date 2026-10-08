"""Vista de saldos: los ajustes de las ventas de granos usan su propia alícuota de IVA (035, 2026-10-08).

La rama `Venta Granos` de `vw_MovimientosCuenta_Base` sumaba los ajustes (`Venta Granos_Ajustes`, p. ej. "A cuenta de
Calidad") al subtotal y le aplicaba a todo el IVA de la venta, ignorando el `AlicuotaIVA` de cada ajuste. Hallado al
comparar FEDEA contra su resumen de cuenta: en tres liquidaciones de 03/2017 la diferencia era exactamente 10,5% del
ajuste de calidad (ajuste con AlicuotaIVA 0). La pantalla de ventas (`calcular_totales`) tiene la misma simplificación.

Uso: `python -m scripts.vista_venta_granos_ajustes_iva --simular` muestra el efecto; sin argumentos aplica
(respaldo verificado, definición anterior en `scripts/vista_base_anterior_ajustes_granos_20261008.sql`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all

VIEJO_CREDITO = """        (
            (CAST(ISNULL(v.[Cantidad vendida], 0) AS float)
                * ((CAST(ISNULL(v.[Precio unitario], 0) AS float) * CAST(ISNULL(v.Factor, 100) AS float) / 100.0
                    - CAST(ISNULL(v.Flete, 0) AS float)) / 1000.0))
            + ISNULL(aj.SumaAjustes, 0)
        ) * (1 + CAST(ISNULL(v.AlicuotaIVA, 0) AS float) / 100.0)"""
NUEVO_CREDITO = """        (
            (CAST(ISNULL(v.[Cantidad vendida], 0) AS float)
                * ((CAST(ISNULL(v.[Precio unitario], 0) AS float) * CAST(ISNULL(v.Factor, 100) AS float) / 100.0
                    - CAST(ISNULL(v.Flete, 0) AS float)) / 1000.0))
        ) * (1 + CAST(ISNULL(v.AlicuotaIVA, 0) AS float) / 100.0)
        + ISNULL(aj.SumaAjustesConIVA, 0)"""
VIEJO_APPLY = "    SELECT SUM(CAST(a.Importe AS float)) AS SumaAjustes\n    FROM dbo.[Venta Granos_Ajustes] a"
NUEVO_APPLY = ("    SELECT SUM(CAST(a.Importe AS float)) AS SumaAjustes,\n"
               "           SUM(CAST(a.Importe AS float) * (1 + CAST(ISNULL(a.AlicuotaIVA, 0) AS float) / 100.0)) AS SumaAjustesConIVA\n"
               "    FROM dbo.[Venta Granos_Ajustes] a")
RESPALDO_DEFINICION = Path(__file__).with_name("vista_base_anterior_ajustes_granos_20261008.sql")


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
        if "SumaAjustesConIVA" in definicion:
            print("La vista ya aplica el IVA propio de cada ajuste.")
            return
        if definicion.count(VIEJO_CREDITO) != 1 or definicion.count(VIEJO_APPLY) != 1:
            raise RuntimeError("No se encontró la rama de Venta Granos con el formato esperado.")
        antes = _saldos()
        nueva = definicion.replace(VIEJO_CREDITO, NUEVO_CREDITO).replace(VIEJO_APPLY, NUEVO_APPLY)
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

        print(f"Respaldo verificado: {backup_verificado('vista-ajustes-granos-iva')}")
        RESPALDO_DEFINICION.write_text(definicion, encoding="utf-8")
        cur.execute(nueva.replace("CREATE VIEW", "ALTER VIEW", 1))
        _comparar(antes, _saldos())
    finally:
        conn.close()


if __name__ == "__main__":
    main("--simular" in sys.argv)
