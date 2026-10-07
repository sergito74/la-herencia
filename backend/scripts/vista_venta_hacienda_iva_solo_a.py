"""Vista de saldos: en las ventas de hacienda el IVA va solo sobre la parte A (035, 2026-10-07).

`vw_MovimientosCuenta_Base` calculaba el crédito de cada venta de hacienda como (A+B − comisión − no gravados) × (1+IVA),
es decir, le aplicaba IVA también a la parte B (en negro). La pantalla de ventas (`calcular_totales`, fórmula confirmada
contra Access) hace: (A − vis. municipal − balanza − comisión − no gravados) × (1+IVA) − sellos − retenciones − gastos + B.
Hallado al comparar el resumen de cuenta de Ferias del Centro con el sistema: sobrevaluaba las ventas con parte B
(Ferias $31.062, Transcom $51.112 —su saldo entero—, J y M de la Serna $283.588, etc.) y, por aplicar vis. municipal y
balanza después del IVA, unos pocos pesos por venta. Decisión de Sergio: alinear la vista con la pantalla.

Uso: `python -m scripts.vista_venta_hacienda_iva_solo_a --simular` muestra el efecto; sin argumentos aplica
(respaldo verificado, definición anterior en `scripts/vista_base_anterior_iva_b_20261007.sql`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all

VIEJO_CREDITO = """    CAST(
        (ISNULL(subtotal.Total, 0) - (ISNULL(subtotal.Total, 0) * ISNULL(v.[Porc Comision], 0) / 100.0)
            - ISNULL(v.[Gs Vs No Gravados], 0))
        * (1 + ISNULL(v.AlicuotaIVA, 0) / 100.0)
        - ISNULL(v.[Ley de Sellos], 0) - ISNULL(v.[Vis Municipal], 0) - ISNULL(v.Balanza, 0)
        - ISNULL(v.Flete, 0) - ISNULL(v.[Gastos Varios], 0) - ISNULL(v.[Retencion Ganancias], 0)
        - ISNULL(v.[Retencion IVA], 0) - ISNULL(v.[Ingresos Brutos], 0) + ISNULL(v.Complemento, 0)
    AS money) AS Credito,
    CAST('Venta Hacienda' AS varchar(50)) AS Origen,"""
NUEVO_CREDITO = """    CAST(
        (ISNULL(subtotal.TotalA, 0) - ISNULL(v.[Vis Municipal], 0) - ISNULL(v.Balanza, 0)
            - ((ISNULL(subtotal.TotalA, 0) + ISNULL(subtotal.TotalB, 0)) * ISNULL(v.[Porc Comision], 0) / 100.0)
            - ISNULL(v.[Gs Vs No Gravados], 0))
        * (1 + ISNULL(v.AlicuotaIVA, 0) / 100.0)
        + ISNULL(subtotal.TotalB, 0)
        - ISNULL(v.[Ley de Sellos], 0)
        - ISNULL(v.Flete, 0) - ISNULL(v.[Gastos Varios], 0) - ISNULL(v.[Retencion Ganancias], 0)
        - ISNULL(v.[Retencion IVA], 0) - ISNULL(v.[Ingresos Brutos], 0) + ISNULL(v.Complemento, 0)
    AS money) AS Credito,
    CAST('Venta Hacienda' AS varchar(50)) AS Origen,"""
VIEJO_APPLY = "    SELECT SUM(d.Cantidad * (ISNULL(d.[Precio unitario (A)], 0) + ISNULL(d.[Precio unitario (B)], 0))) AS Total\n    FROM dbo.[Det_Ventas Hacienda] d"
NUEVO_APPLY = ("    SELECT SUM(d.Cantidad * (ISNULL(d.[Precio unitario (A)], 0) + ISNULL(d.[Precio unitario (B)], 0))) AS Total,\n"
               "           SUM(d.Cantidad * ISNULL(d.[Precio unitario (A)], 0)) AS TotalA,\n"
               "           SUM(d.Cantidad * ISNULL(d.[Precio unitario (B)], 0)) AS TotalB\n"
               "    FROM dbo.[Det_Ventas Hacienda] d")
RESPALDO_DEFINICION = Path(__file__).with_name("vista_base_anterior_iva_b_20261007.sql")


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
        if "subtotal.TotalB" in definicion:
            print("La vista ya aplica el IVA solo sobre la parte A.")
            return
        if definicion.count(VIEJO_CREDITO) != 1 or definicion.count(VIEJO_APPLY) != 1:
            raise RuntimeError("No se encontró la rama de Venta Hacienda con el formato esperado.")
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

        print(f"Respaldo verificado: {backup_verificado('vista-venta-hacienda-iva-a')}")
        RESPALDO_DEFINICION.write_text(definicion, encoding="utf-8")
        cur.execute(nueva.replace("CREATE VIEW", "ALTER VIEW", 1))
        _comparar(antes, _saldos())
    finally:
        conn.close()


if __name__ == "__main__":
    main("--simular" in sys.argv)
