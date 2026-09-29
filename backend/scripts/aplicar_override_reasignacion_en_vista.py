"""Aplica el mecanismo de reasignación de contacto (022) sobre
`vw_MovimientosCuenta_Base`: envuelve el cuerpo existente de la vista (sin
modificar ninguna de sus ramas — ver
`scripts/agregar_tarjetas_a_vista_cuenta_corriente.py`) en una subconsulta
`base`, y aplica un `OUTER APPLY` a `dbo.ReasignacionesContacto` que
sustituye `IdContacto`/`[Razon Social]` por el override vigente (la última
fila para ese `(Origen, IdOrigen)`) cuando existe uno.

Esto nunca escribe en `Movimientos Galicia`/`Movimientos BNA`/`Compras`:
toda reasignación queda en `ReasignacionesContacto` (spec 022, FR-014).
Ver research.md §3 (specs/022-reasignacion-contacto/research.md).

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.aplicar_override_reasignacion_en_vista
"""

import pyodbc

from scripts.agregar_tarjetas_a_vista_cuenta_corriente import DDL_ALTER_VISTA as _DDL_BASE
from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

_marker = "AS\n\n"
_prefijo, _cuerpo = _DDL_BASE.split(_marker, 1)
assert _prefijo.strip() == "ALTER VIEW dbo.vw_MovimientosCuenta_Base"
_cuerpo_sin_punto_y_coma = _cuerpo.rstrip().rstrip(";")

DDL_ALTER_VISTA_CON_OVERRIDE = f"""
ALTER VIEW dbo.vw_MovimientosCuenta_Base
AS

SELECT
    base.Fecha,
    COALESCE(ov.IdContactoNuevo, base.IdContacto) AS IdContacto,
    COALESCE(ctov.[Razon Social], base.[Razon Social]) AS [Razon Social],
    base.Documento,
    base.[Nro Documento],
    base.Deuda,
    base.Credito,
    base.Origen,
    base.IdOrigen
FROM (
{_cuerpo_sin_punto_y_coma}
) AS base
OUTER APPLY (
    SELECT TOP 1 r.IdContactoNuevo
    FROM dbo.ReasignacionesContacto r
    WHERE r.Origen = base.Origen AND r.IdOrigen = base.IdOrigen
    ORDER BY r.IdReasignacion DESC
) AS ov
LEFT JOIN dbo.Contactos AS ctov ON ctov.IdContacto = ov.IdContactoNuevo;
"""


def main() -> None:
    _assert_target_is_wc()
    print(f"Conectando a {DATABASE}...")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()
        cursor.execute(DDL_ALTER_VISTA_CON_OVERRIDE)
        print("OK: dbo.vw_MovimientosCuenta_Base ahora aplica el override de dbo.ReasignacionesContacto.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
