"""Cuenta corriente: cada línea de tarjeta suma exactamente su importe (2026-10-01).

Bug hallado al cerrar las conciliaciones de tarjetas pendientes: la vista
`vw_MovimientosCuenta_Base` mostraba una línea de tarjeta de dos formas
excluyentes:

- rama 'Tarjetas': solo lo vinculado a facturas, y solo si la factura tiene
  `GranTotal > 0` (los vínculos con notas de crédito no aparecían);
- rama 'Tarjeta sin imputar': la línea entera, pero solo si NO tenía ningún
  vínculo.

Una línea vinculada en parte (agrupada, cuota, FIFO parcial) perdía el resto, y
una vinculada a factura + NC quedaba con el crédito inflado.

Corrección:
- rama 'Tarjetas': `GranTotal <> 0`, así los vínculos con NC restan el pago;
- rama 'Tarjeta sin imputar': para cada línea con contacto, `Importe − todo lo
  vinculado` cuando es distinto de cero (el resto de una línea parcial).
Los vínculos con facturas de total 0 (cargadas sin importe) siguen sin mostrarse,
igual que la factura: sumar el pago sin la deuda inventaría saldo a favor.
Idempotente, con respaldo verificado. `--simular` muestra el efecto por contacto.

Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.vista_tarjeta_resto_linea [--simular]
"""

import sys

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all

MARCA = "-- resto-linea-v2"

SELECT_RESTO = f"""
SELECT {MARCA}
    l.FechaCompra AS Fecha,
    l.IdContacto,
    ct.[Razon Social],
    CAST('Tarjeta sin imputar' AS varchar(50)) AS Documento,
    CAST(rs.ResumenCodigo AS varchar(50)) AS [Nro Documento],
    CASE WHEN x.resto < 0 THEN -x.resto ELSE CAST(0 AS money) END AS Deuda,
    CASE WHEN x.resto > 0 THEN x.resto ELSE CAST(0 AS money) END AS Credito,
    CAST('Tarjeta sin imputar' AS varchar(50)) AS Origen,
    CAST(l.IdLineaConsumo AS bigint) AS IdOrigen
FROM dbo.Tarjetas_Resumenes_Lineas AS l
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = l.IdContacto
LEFT JOIN dbo.Tarjetas_Resumenes AS rs ON rs.IdResumen = l.IdResumen
CROSS APPLY (
    SELECT CAST(ISNULL(l.Importe, 0) - ISNULL((
        SELECT SUM(v.ImporteImputado)
        FROM dbo.Tarjetas_Resumenes_Lineas_Compras AS v
        WHERE v.IdLineaConsumo = l.IdLineaConsumo
    ), 0) AS money) AS resto
) AS x
WHERE ABS(x.resto) > 0.005
"""

VIEJA_INICIO = "SELECT\n    l.FechaCompra AS Fecha,\n    l.IdContacto,\n    ct.[Razon Social],\n    CAST('Tarjeta sin imputar'"
VIEJA_FIN = "WHERE ISNULL(l.Importe, 0) <> 0\n  AND NOT EXISTS (SELECT 1 FROM dbo.Tarjetas_Resumenes_Lineas_Compras lc WHERE lc.IdLineaConsumo = l.IdLineaConsumo)\n"


FILTRO_TARJETAS = "WHERE tc.GranTotal > 0\n  AND ISNULL(v.ImporteImputado, 0) <> 0"


def _nueva_definicion(definicion: str) -> str:
    i = definicion.find(VIEJA_INICIO)
    j = definicion.find(VIEJA_FIN, i)
    if i < 0 or j < 0 or definicion.count(VIEJA_INICIO) != 1:
        raise RuntimeError("No se encontró la rama 'Tarjeta sin imputar' original en la vista.")
    nueva = definicion[:i] + SELECT_RESTO.strip("\n") + "\n" + definicion[j + len(VIEJA_FIN):]
    if nueva.count(FILTRO_TARJETAS) != 1:
        raise RuntimeError("No se encontró el filtro de la rama 'Tarjetas'.")
    return nueva.replace(FILTRO_TARJETAS, "WHERE tc.GranTotal <> 0\n  AND ISNULL(v.ImporteImputado, 0) <> 0")


def simular() -> None:
    vieja = fetch_all("""
        SELECT l.IdContacto AS k, SUM(l.Importe) AS s FROM dbo.Tarjetas_Resumenes_Lineas l
        WHERE l.IdContacto IS NOT NULL AND ISNULL(l.Importe,0) <> 0
          AND NOT EXISTS (SELECT 1 FROM dbo.Tarjetas_Resumenes_Lineas_Compras lc WHERE lc.IdLineaConsumo = l.IdLineaConsumo)
        GROUP BY l.IdContacto""")
    nueva = fetch_all(f"SELECT IdContacto AS k, SUM(Credito - Deuda) AS s FROM ({SELECT_RESTO}) q GROUP BY IdContacto")
    a = {r["k"]: float(r["s"]) for r in vieja}
    b = {r["k"]: float(r["s"]) for r in nueva}
    nombres = {r["id"]: r["rs"] for r in fetch_all("SELECT IdContacto id, [Razon Social] rs FROM dbo.Contactos")}
    cambios = sorted(((k, b.get(k, 0) - a.get(k, 0)) for k in set(a) | set(b)), key=lambda t: -abs(t[1]))
    cambios = [c for c in cambios if abs(c[1]) > 0.005]
    print(f"Contactos cuyo crédito por tarjeta cambia: {len(cambios)}")
    for k, d in cambios:
        print(f"  {k:4} {str(nombres.get(k))[:32]:32} crédito {d:>+15,.2f}")


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo sobre WC")
        definicion = cur.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_MovimientosCuenta_Base'))").fetchone()[0]
        definicion = definicion.replace("\r\n", "\n")
        if MARCA in definicion:
            print("La vista ya muestra el resto de cada línea.")
            return
        nueva = _nueva_definicion(definicion).replace("CREATE VIEW", "ALTER VIEW", 1)
        from src.features.vinculos.backup import backup_verificado
        print(f"Respaldo verificado: {backup_verificado('vista-tarjeta-resto-linea')}")
        cur.execute(nueva)
        print("Vista corregida: cada línea de tarjeta suma su importe completo.")
    finally:
        conn.close()


if __name__ == "__main__":
    simular() if "--simular" in sys.argv else main()
