"""Pagos que los socios hicieron por cuenta de la empresa, en la cuenta del proveedor (2026-10-01).

La migración 027 cargó "Cajas Giamigli.xlsx" en MovimientosCuentaSocio. Un
movimiento 'Devolucion' es un pago que el socio hizo con fondos propios por
cuenta de la empresa (por ejemplo, la factura 225213 de la Cooperativa
Eléctrica, pagada desde la cuenta de Sergio el 13/07/2026). Ese pago estaba en
la cuenta del socio pero no en la del proveedor, así que el proveedor
quedaba con deuda.

1. **`PagosSocioProveedor`** (IdMovimientoSocio → IdContacto): el proveedor
   sale del texto anterior a " — " en el Motivo. Se compara por nombre
   normalizado contra Contactos, con un alias manual para los nombres
   genéricos (ARCA → AFIP, Tasa Vial → Municipalidad, etc.).
2. **Exclusiones**:
   - Pagos que ya figuran en la cuenta del proveedor por otro medio (mismo
     contacto, importe ±$1, ±7 días). El Access registraba muchos en las
     cajas "Particular L/S".
   - Aportes y retiros.
   - Contactos que son socios o la empresa: Condominio LSC, Giamigli,
     Sergio Giamberardini.
3. **Vista**: se agrega la rama 'Pago por socio' (Crédito del proveedor).

Es idempotente y hace un respaldo verificado antes de cambiar algo.

Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.vincular_pagos_socios [--aplicar]
"""

from __future__ import annotations

import re
import sys
import unicodedata
from collections import defaultdict

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, execute_write_transaction, fetch_all

ALIAS = {"arca": 119, "afip": 119, "tasa vial": 72, "imp inmobiliario": 12, "armando mori": 376,
         "franco rodriguez": 379, "mario gorosito": 566, "sindicato uatre": 315}
EXCLUIR_CONTACTOS = {549, 386, 375}  # Condominio LSC, Giamigli de Bolívar, Sergio Giamberardini
NO_PROVEEDOR = ("aporte", "retiro", "cambio", "transferencia")

DDL = """
IF OBJECT_ID('dbo.PagosSocioProveedor', 'U') IS NULL
CREATE TABLE dbo.PagosSocioProveedor (
    IdMovimientoSocio int          NOT NULL PRIMARY KEY,
    IdContacto        int          NOT NULL,
    Criterio          varchar(20)  NOT NULL,
    FechaAlta         datetime2    NOT NULL DEFAULT SYSDATETIME()
)
"""

RAMA = """

UNION ALL

SELECT
    CAST(ms.Fecha AS datetime) AS Fecha,
    psp.IdContacto,
    ct.[Razon Social],
    CAST('Pago por socio' AS varchar(50)) AS Documento,
    CAST(so.Nombre AS varchar(50)) AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(ms.Importe AS money) AS Credito,
    CAST('Pago por socio' AS varchar(50)) AS Origen,
    CAST(ms.IdMovimiento AS bigint) AS IdOrigen
FROM dbo.PagosSocioProveedor AS psp
INNER JOIN dbo.MovimientosCuentaSocio AS ms ON ms.IdMovimiento = psp.IdMovimientoSocio AND ms.Anulada = 0
INNER JOIN dbo.Socios AS so ON so.IdSocio = ms.IdSocio
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = psp.IdContacto
WHERE ISNULL(ms.Importe, 0) > 0
"""
MARCA_FIN = "\n\n) AS base\nOUTER APPLY ("


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(s\.?a\.?|s\.?r\.?l\.?|sa|srl|s\.a\.s|ltda|de|del|la|el|y)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def proponer() -> list[tuple]:
    indice = defaultdict(set)
    for c in fetch_all("SELECT IdContacto AS id, [Razon Social] AS rs FROM dbo.Contactos"):
        indice[_norm(c["rs"])].add(c["id"])
    existentes = {f["id"] for f in fetch_all("SELECT IdMovimientoSocio AS id FROM dbo.PagosSocioProveedor")} \
        if fetch_all("SELECT OBJECT_ID('dbo.PagosSocioProveedor') AS o")[0]["o"] else set()
    propuestas = []
    for m in fetch_all("SELECT IdMovimiento AS id, Importe AS imp, CAST(Fecha AS date) AS f, Motivo AS mot "
                       "FROM dbo.MovimientosCuentaSocio WHERE Tipo = 'Devolucion' AND Anulada = 0 AND Importe > 0"):
        if m["id"] in existentes:
            continue
        n = _norm((m["mot"] or "").split(" — ")[0])
        if not n or n.startswith(NO_PROVEEDOR):
            continue
        if n.startswith("autonomos"):
            contacto, criterio = 119, "alias"
        elif n in ALIAS:
            contacto, criterio = ALIAS[n], "alias"
        else:
            ids = indice.get(n)
            if not ids:
                cand = {i for k, v in indice.items() if k and (k.startswith(n) or n.startswith(k))
                        and min(len(k), len(n)) >= 4 for i in v}
                ids = cand if len(cand) == 1 else None
            if not ids or len(ids) != 1:
                continue
            contacto, criterio = next(iter(ids)), "nombre"
        if contacto in EXCLUIR_CONTACTOS:
            continue
        ya = fetch_all("SELECT TOP 1 1 AS x FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ? "
                       "AND ABS(DATEDIFF(day, Fecha, ?)) <= 7 AND ABS(Credito - ?) <= 1",
                       (contacto, m["f"], float(m["imp"])))
        if ya:
            continue
        propuestas.append((m["id"], contacto, criterio, float(m["imp"]), m["mot"]))
    return propuestas


def main(aplicar: bool) -> None:
    _assert_target_is_wc()
    propuestas = proponer()
    print(f"Pagos de socios a vincular: {len(propuestas)} (${sum(p[3] for p in propuestas):,.2f})")
    if not aplicar:
        for p in propuestas[:40]:
            print(f"  mov {p[0]:5} -> contacto {p[1]:4} ({p[2]}) ${p[3]:>12,.2f}  {p[4][:60]}")
        print("Simulación: no se escribió nada. Usar --aplicar para grabar.")
        return
    from src.features.vinculos.backup import backup_verificado
    print(f"Respaldo verificado: {backup_verificado('pagos-socios-proveedor')}")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cur = conn.cursor()
        cur.execute(DDL)
        definicion = cur.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_MovimientosCuenta_Base'))").fetchone()[0]
        definicion = definicion.replace("\r\n", "\n")
        if "'Pago por socio'" not in definicion:
            if definicion.count(MARCA_FIN) != 1:
                raise RuntimeError("No se encontró el cierre de la unión en la vista.")
            cur.execute(definicion.replace(MARCA_FIN, RAMA + MARCA_FIN).replace("CREATE VIEW", "ALTER VIEW", 1))
            print("Vista ampliada con 'Pago por socio'.")
    finally:
        conn.close()
    if propuestas:
        execute_write_transaction([("INSERT INTO dbo.PagosSocioProveedor (IdMovimientoSocio, IdContacto, Criterio) "
                                    "VALUES (?, ?, ?)", (p[0], p[1], p[2])) for p in propuestas])
    print(f"Vinculados {len(propuestas)} pagos de socios.")


if __name__ == "__main__":
    main(aplicar="--aplicar" in sys.argv)
