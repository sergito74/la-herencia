"""Vista de saldos: los pagos con tarjeta de facturas de total $0 entran siempre (035, 2026-10-07).

La rama 'Tarjetas' de `vw_MovimientosCuenta_Base` filtraba `tc.GranTotal <> 0`. Una factura 100% personal
(compra particular neteada a $0) guarda un resto de redondeo (p. ej. -5,7e-13) que según la forma de la consulta
vale 0 exacto o no: el pago con tarjeta entraba o no al saldo de la cuenta de manera inestable (43 vínculos entraban,
26 quedaban afuera; caso Coto, factura 2184-00133702 con dos líneas de tarjeta). Decisión de Sergio: entran todos,
la empresa pagó con su tarjeta y ese pago debe verse en la cuenta; la parte del socio se compensa con el asiento
"Particular" / la deuda del socio.

Uso: `python -m scripts.vista_tarjeta_incluir_total_cero --simular` muestra el efecto; sin argumentos aplica
(respaldo verificado, guarda la definición anterior en `scripts/vista_base_anterior_20261007.sql`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all

FILTRO = "WHERE tc.GranTotal <> 0\n  AND ISNULL(v.ImporteImputado, 0) <> 0"
NUEVO = "WHERE ISNULL(v.ImporteImputado, 0) <> 0"
RESPALDO_DEFINICION = Path(__file__).with_name("vista_base_anterior_20261007.sql")


def _saldos(vista: str = "vw_MovimientosCuenta_Base") -> dict[int, float]:
    return {r["k"]: float(r["s"]) for r in fetch_all(
        f"SELECT IdContacto AS k, SUM(Credito - Deuda) AS s FROM dbo.{vista} GROUP BY IdContacto")}


def _nombres() -> dict[int, str]:
    return {r["id"]: r["rs"] for r in fetch_all("SELECT IdContacto id, [Razon Social] rs FROM dbo.Contactos")}


def _comparar(antes: dict[int, float], despues: dict[int, float]) -> None:
    nombres = _nombres()
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
        if FILTRO not in definicion:
            print("La vista ya incluye las facturas de total cero (o el filtro cambió).")
            return
        if definicion.count(FILTRO) != 1:
            raise RuntimeError("El filtro aparece más de una vez.")
        antes = _saldos()
        nueva = definicion.replace(FILTRO, NUEVO)
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

        print(f"Respaldo verificado: {backup_verificado('vista-tarjeta-total-cero')}")
        RESPALDO_DEFINICION.write_text(definicion, encoding="utf-8")
        cur.execute(nueva.replace("CREATE VIEW", "ALTER VIEW", 1))
        _comparar(antes, _saldos())
    finally:
        conn.close()


if __name__ == "__main__":
    main("--simular" in sys.argv)
