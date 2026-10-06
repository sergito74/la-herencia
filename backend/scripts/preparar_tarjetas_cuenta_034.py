"""034 — Prepara la cuenta de la administración anterior de AgroNacion.

Los pagos de septiembre de 2010 a junio de 2012 corresponden a la administración
anterior de la tarjeta (Oscar y Albina) y a resúmenes que se tomaron como saldo
inicial (estado `Cerrado`, 571 a 578): no pertenecen a la cuenta vigente. Este
script crea el contacto "AgroNacion (administración anterior)" y reasigna a él,
con `ReasignacionesContacto` (el mecanismo no destructivo de la vista), los 22 pagos:

  * 21 de `Movimientos BNA` con concepto "PM/TOT. RES. AGRONACION", del 28/09/2010 al
    28/05/2012, que suman exactamente $23.575,00 y no están ligados a ningún resumen;
  * 1 de `Pagos efectivo` (IdPagoEfectivo 363, 26/06/2012, $1.677,58).

Aborta si el conjunto no coincide exactamente. Requiere haber ejecutado antes
`scripts.vista_tarjeta_cuenta_corriente` (usa `dbo.TarjetasContacto`).

Uso (desde backend/):
    python -m scripts.preparar_tarjetas_cuenta_034 --verificar   # no escribe
    python -m scripts.preparar_tarjetas_cuenta_034               # respaldo verificado y escritura
    python -m scripts.preparar_tarjetas_cuenta_034 --revertir    # deshace las reasignaciones
"""

from __future__ import annotations

import sys

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc

ID_TARJETA_AGRONACION = 1
ID_CONTACTO_AGRONACION = 373
NOMBRE_ANTERIOR = "AgroNacion (administración anterior)"
USUARIO = "preparacion-034"
MOTIVO = "Saldo inicial: pago de la administración anterior (Oscar y Albina), 034-cuenta-corriente-tarjetas"
ESPERADOS_BNA = {"cantidad": 21, "importe": 23575.00, "desde": "2010-09-28", "hasta": "2012-05-28"}
ESPERADO_EFECTIVO = {"id": 363, "fecha": "2012-06-26", "importe": 1677.58}


def _conexion(autocommit: bool = True):
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=autocommit)
    if conn.cursor().execute("SELECT DB_NAME()").fetchone()[0] != "WC":
        conn.close()
        raise RuntimeError("Solo sobre WC")
    return conn


def _pagos_de_la_administracion_anterior(cur) -> list[tuple[str, int]]:
    """Devuelve [(origen, id)] y valida que sean exactamente los esperados."""
    bna = cur.execute(
        """
        SELECT b.IdMovimientoBNA, -b.Importe, CONVERT(varchar(10), b.[Fecha / Hora Mov#], 23)
        FROM dbo.[Movimientos BNA] b
        WHERE b.IdContacto = ? AND b.Concepto LIKE 'PM/TOT. RES. AGRONACION%'
          AND b.[Fecha / Hora Mov#] >= ? AND b.[Fecha / Hora Mov#] < DATEADD(day, 1, CAST(? AS date))
          AND NOT EXISTS (SELECT 1 FROM dbo.Tarjetas_Resumenes_Pagos p
                          WHERE p.Origen = 'BNA' AND p.IdMovimientoOrigen = b.IdMovimientoBNA)
        """,
        ID_CONTACTO_AGRONACION, ESPERADOS_BNA["desde"], ESPERADOS_BNA["hasta"],
    ).fetchall()
    total_bna = round(sum(float(f[1]) for f in bna), 2)
    if len(bna) != ESPERADOS_BNA["cantidad"] or abs(total_bna - ESPERADOS_BNA["importe"]) > 0.005:
        raise RuntimeError(f"Los pagos del Banco Nación no coinciden: {len(bna)} movimientos por {total_bna:,.2f}")
    efectivo = cur.execute(
        "SELECT IdPagoEfectivo, [Importe imputado], CONVERT(varchar(10), Fecha, 23) FROM dbo.[Pagos efectivo] "
        "WHERE IdPagoEfectivo = ? AND IdContacto = ?", ESPERADO_EFECTIVO["id"], ID_CONTACTO_AGRONACION).fetchone()
    if (not efectivo or efectivo[2] != ESPERADO_EFECTIVO["fecha"]
            or abs(float(efectivo[1]) - ESPERADO_EFECTIVO["importe"]) > 0.005):
        raise RuntimeError("El pago en efectivo del 26/06/2012 no coincide con lo esperado")
    return [("Banco Nacion", f[0]) for f in bna] + [("Pagos efectivo", efectivo[0])]


def _tabla_mapeo_lista(cur) -> bool:
    return cur.execute("SELECT OBJECT_ID('dbo.TarjetasContacto', 'U')").fetchone()[0] is not None


def _contacto_anterior(cur) -> int | None:
    fila = cur.execute("SELECT IdContacto FROM dbo.Contactos WHERE [Razon Social] = ?", NOMBRE_ANTERIOR).fetchone()
    return fila[0] if fila else None


def _ya_reasignados(cur, pagos: list[tuple[str, int]]) -> int:
    n = 0
    for origen, id_origen in pagos:
        n += cur.execute("SELECT COUNT(*) FROM dbo.ReasignacionesContacto WHERE Origen = ? AND IdOrigen = ? AND Usuario = ?",
                         origen, id_origen, USUARIO).fetchone()[0]
    return n


def verificar() -> None:
    conn = _conexion()
    try:
        cur = conn.cursor()
        pagos = _pagos_de_la_administracion_anterior(cur)
        print(f"Pagos de la administración anterior identificados: {len(pagos)} "
              f"(21 del Banco Nación por $23.575,00 y 1 en efectivo por $1.677,58; total $25.252,58)")
        print(f"Tabla TarjetasContacto: {'lista' if _tabla_mapeo_lista(cur) else 'NO existe (ejecutar antes scripts.vista_tarjeta_cuenta_corriente)'}")
        print(f"Contacto \"{NOMBRE_ANTERIOR}\": {'ya existe, id ' + str(_contacto_anterior(cur)) if _contacto_anterior(cur) else 'se creará'}")
        print(f"Reasignaciones ya hechas por este script: {_ya_reasignados(cur, pagos)}")
        print("Solo verificación: no se escribió nada.")
    finally:
        conn.close()


def aplicar() -> None:
    from src.features.vinculos.backup import backup_verificado

    conn = _conexion(autocommit=False)
    try:
        cur = conn.cursor()
        if not _tabla_mapeo_lista(cur):
            raise SystemExit("Falta dbo.TarjetasContacto: ejecutá antes scripts.vista_tarjeta_cuenta_corriente.")
        pagos = _pagos_de_la_administracion_anterior(cur)
        if _ya_reasignados(cur, pagos) == len(pagos):
            print("Los 22 pagos ya estaban reasignados: no se hace nada.")
            return
        conn.rollback()
        print(f"Respaldo verificado: {backup_verificado('preparar-tarjetas-034')}")
        id_anterior = _contacto_anterior(cur)
        if id_anterior is None:
            id_anterior = cur.execute(
                "INSERT INTO dbo.Contactos ([Tipo Contacto], [Razon Social], EsContratistaLabores) "
                "OUTPUT INSERTED.IdContacto VALUES ('Tarjeta de Credito', ?, 0)", NOMBRE_ANTERIOR).fetchone()[0]
            print(f"Contacto creado: {NOMBRE_ANTERIOR} (id {id_anterior})")
        nuevas = 0
        for origen, id_origen in pagos:
            existe = cur.execute("SELECT 1 FROM dbo.ReasignacionesContacto WHERE Origen = ? AND IdOrigen = ? AND Usuario = ?",
                                 origen, id_origen, USUARIO).fetchone()
            if existe:
                continue
            cur.execute(
                "INSERT INTO dbo.ReasignacionesContacto (Origen, IdOrigen, IdContactoAnterior, IdContactoNuevo, Motivo, Usuario) "
                "VALUES (?, ?, ?, ?, ?, ?)", origen, id_origen, ID_CONTACTO_AGRONACION, id_anterior, MOTIVO, USUARIO)
            nuevas += 1
        cur.execute("UPDATE dbo.TarjetasContacto SET IdContactoAnterior = ? WHERE IdTarjeta = ?", id_anterior, ID_TARJETA_AGRONACION)
        conn.commit()
        print(f"Reasignaciones nuevas: {nuevas}; contacto anterior de AgroNacion = {id_anterior}.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def revertir() -> None:
    conn = _conexion(autocommit=False)
    try:
        cur = conn.cursor()
        borradas = cur.execute("DELETE FROM dbo.ReasignacionesContacto WHERE Usuario = ? AND Motivo = ?", USUARIO, MOTIVO).rowcount
        if _tabla_mapeo_lista(cur):
            cur.execute("UPDATE dbo.TarjetasContacto SET IdContactoAnterior = NULL WHERE IdTarjeta = ?", ID_TARJETA_AGRONACION)
        id_anterior = _contacto_anterior(cur)
        if id_anterior is not None:
            usos = cur.execute("SELECT COUNT(*) FROM dbo.ReasignacionesContacto WHERE IdContactoNuevo = ?", id_anterior).fetchone()[0]
            if usos == 0:
                cur.execute("DELETE FROM dbo.Contactos WHERE IdContacto = ? AND [Razon Social] = ?", id_anterior, NOMBRE_ANTERIOR)
                print(f"Contacto {id_anterior} eliminado (no tenía otros usos).")
        conn.commit()
        print(f"Reasignaciones deshechas: {borradas}.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main(argv: list[str]) -> None:
    if "--verificar" in argv:
        verificar()
    elif "--revertir" in argv:
        revertir()
    else:
        aplicar()


if __name__ == "__main__":
    main(sys.argv[1:])
