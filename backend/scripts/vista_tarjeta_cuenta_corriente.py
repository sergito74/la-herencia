"""034 — Cuentas de tarjetas y de Mercado Pago: tablas y ramas de la vista compartida.

Crea `dbo.TarjetasContacto` y `dbo.TarjetasCruces` y agrega cinco ramas a
`vw_MovimientosCuenta_Base` (sin tocar las existentes):

  * `Tarjeta consumo`     deuda por cada consumo, en la fecha del consumo.
  * `Tarjeta cargo`       cargos propios del resumen, en la fecha de cierre.
  * `Tarjeta devolución`  contrapartida de un débito devuelto (cruce aprobado).
  * `Tarjeta pago`        pagos de resumen que no tienen movimiento bancario (hoy uno, "Crédito banco").
  * `Mercado Pago`        pagos de la billetera con contacto asignado, sin conciliar
                          y que no sean "conducto" (ingreso desde un banco propio y pago
                          de la misma operación, mismo día e importe opuesto).

Modos (specs/034-cuenta-corriente-tarjetas/quickstart.md):

  --verificar   no escribe: valida el estado y cuenta lo que aportaría cada rama.
  --ensayo      hace todo dentro de una transacción y la revierte: no deja cambios.
  (sin opción)  respaldo verificado, instantánea previa, tablas y ramas (idempotente).
  --comparar    compara los saldos y el flujo de caja actuales con la instantánea previa.
  --revertir    restaura la definición previa de la vista (las tablas quedan).

Uso (desde backend/):  python -m scripts.vista_tarjeta_cuenta_corriente [opción]
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc

VISTA = "dbo.vw_MovimientosCuenta_Base"
CARPETA = Path(r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Auditoria cuentas corrientes")
ARCHIVO_INSTANTANEA = CARPETA / "instantanea_034_antes.json"
ARCHIVO_VISTA_PREVIA = CARPETA / "vw_MovimientosCuenta_Base_previa_034.sql"

MARCA_FIN = "\n\n) AS base\nOUTER APPLY ("
ORIGENES_NUEVOS = ("Tarjeta consumo", "Tarjeta cargo", "Tarjeta devolución", "Tarjeta pago", "Mercado Pago")

# Tarjeta -> contacto (regla vigente de 008: nombre igual y Tipo Contacto = 'Tarjeta de Credito').
TARJETAS_ESPERADAS = {1: 373, 2: 503, 3: 372, 4: 532, 5: 533}

# Excepción esperada de FR-005: único contacto no tarjeta que cambia (pago ML del 04/09/2024).
CONTACTO_UATRE, DIFERENCIA_UATRE = 315, 17185.82

DDL_TARJETAS_CONTACTO = """
IF OBJECT_ID('dbo.TarjetasContacto', 'U') IS NULL
CREATE TABLE dbo.TarjetasContacto (
    IdTarjeta int NOT NULL CONSTRAINT PK_TarjetasContacto PRIMARY KEY,
    IdContacto int NOT NULL CONSTRAINT UQ_TarjetasContacto_Contacto UNIQUE,
    IdContactoAnterior int NULL,
    Usuario varchar(60) NULL,
    Fecha datetime2 NOT NULL CONSTRAINT DF_TarjetasContacto_Fecha DEFAULT SYSDATETIME(),
    CONSTRAINT FK_TarjetasContacto_Tarjeta FOREIGN KEY (IdTarjeta) REFERENCES dbo.Tarjetas (IdTarjeta),
    CONSTRAINT FK_TarjetasContacto_Contacto FOREIGN KEY (IdContacto) REFERENCES dbo.Contactos (IdContacto)
)
"""

DDL_TARJETAS_CRUCES = """
IF OBJECT_ID('dbo.TarjetasCruces', 'U') IS NULL
CREATE TABLE dbo.TarjetasCruces (
    IdCruce int IDENTITY(1,1) NOT NULL CONSTRAINT PK_TarjetasCruces PRIMARY KEY,
    Tipo varchar(30) NOT NULL
        CONSTRAINT CK_TarjetasCruces_Tipo CHECK (Tipo IN ('devolucion-debito', 'consumo-devolucion')),
    IdTarjeta int NOT NULL CONSTRAINT FK_TarjetasCruces_Tarjeta REFERENCES dbo.Tarjetas (IdTarjeta),
    MedioOrigen varchar(20) NOT NULL,
    IdMovimientoOrigen int NOT NULL,
    MedioDestino varchar(20) NULL,
    IdMovimientoDestino int NULL,
    IdLineaConsumo int NULL,
    Importe money NOT NULL CONSTRAINT CK_TarjetasCruces_Importe CHECK (Importe > 0),
    Sugerido bit NOT NULL CONSTRAINT DF_TarjetasCruces_Sugerido DEFAULT 0,
    Usuario varchar(60) NULL,
    Fecha datetime2 NOT NULL CONSTRAINT DF_TarjetasCruces_Fecha DEFAULT SYSDATETIME(),
    Deshecho bit NOT NULL CONSTRAINT DF_TarjetasCruces_Deshecho DEFAULT 0,
    UsuarioDeshecho varchar(60) NULL,
    FechaDeshecho datetime2 NULL,
    CONSTRAINT CK_TarjetasCruces_Devolucion CHECK
        (Tipo <> 'devolucion-debito' OR (MedioDestino IS NOT NULL AND IdMovimientoDestino IS NOT NULL)),
    CONSTRAINT CK_TarjetasCruces_Consumo CHECK
        (Tipo <> 'consumo-devolucion' OR IdLineaConsumo IS NOT NULL)
)
"""

# Un movimiento no puede estar en dos cruces vigentes a la vez.
DDL_INDICE_CRUCES = """
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_TarjetasCruces_Origen' AND object_id = OBJECT_ID('dbo.TarjetasCruces'))
CREATE UNIQUE INDEX UX_TarjetasCruces_Origen ON dbo.TarjetasCruces (MedioOrigen, IdMovimientoOrigen) WHERE Deshecho = 0
"""

# Cada cargo del resumen: (n, nombre, columna). `IdOrigen = IdResumen * 100 + n`.
CARGOS = (
    (1, "Impuesto de sellos", "ImpuestoSellos"), (2, "Gastos administrativos", "GastosAdmin"),
    (3, "Mantenimiento de cuenta", "MantCuenta"), (4, "Renovación anual", "RenovAnual"),
    (5, "Promoción BNA", "PromocionBNA"), (6, "Crédito contingente", "CreditoContingente"),
    (7, "Interés financiero", "IntFinanc"), (8, "Interés compensatorio", "IntCompens"),
    (9, "IVA 10,5%", "IVA105"), (10, "Percepción IVA 10,5%", "PercepIVA105"),
    (11, "IVA 21%", "IVA21"), (12, "Percepción IVA 21%", "PercepIVA21"),
    (13, "Percepción IIBB", "PercepIIBB"), (14, "Ajuste resumen anterior", "AjusteResAnterior"),
)
_VALORES_CARGOS = ",\n        ".join(f"({n}, N'{nombre}', rs.{col})" for n, nombre, col in CARGOS)

RAMA_CONSUMO = """
SELECT
    l.FechaCompra AS Fecha,
    tc.IdContacto AS IdContacto,
    ct.[Razon Social],
    CAST('Consumo tarjeta' AS varchar(50)) AS Documento,
    CAST(rs.ResumenCodigo AS varchar(50)) AS [Nro Documento],
    CASE WHEN ISNULL(l.Importe, 0) > 0 THEN CAST(l.Importe AS money) ELSE CAST(0 AS money) END AS Deuda,
    CASE WHEN ISNULL(l.Importe, 0) < 0 THEN CAST(-l.Importe AS money) ELSE CAST(0 AS money) END AS Credito,
    CAST('Tarjeta consumo' AS varchar(50)) AS Origen,
    CAST(l.IdLineaConsumo AS bigint) AS IdOrigen
FROM dbo.Tarjetas_Resumenes_Lineas AS l
INNER JOIN dbo.Tarjetas_Resumenes AS rs ON rs.IdResumen = l.IdResumen
INNER JOIN dbo.TarjetasContacto AS tc ON tc.IdTarjeta = rs.IdTarjeta
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = tc.IdContacto
WHERE ISNULL(rs.EstadoResumen, '') <> 'Cerrado' AND ISNULL(l.Importe, 0) <> 0
"""

RAMA_CARGO = f"""
SELECT
    rs.FechaCierre AS Fecha,
    tc.IdContacto AS IdContacto,
    ct.[Razon Social],
    CAST(cg.Nombre AS varchar(50)) AS Documento,
    CAST(rs.ResumenCodigo AS varchar(50)) AS [Nro Documento],
    CASE WHEN cg.Importe > 0 THEN CAST(cg.Importe AS money) ELSE CAST(0 AS money) END AS Deuda,
    CASE WHEN cg.Importe < 0 THEN CAST(-cg.Importe AS money) ELSE CAST(0 AS money) END AS Credito,
    CAST('Tarjeta cargo' AS varchar(50)) AS Origen,
    CAST(rs.IdResumen * 100 + cg.N AS bigint) AS IdOrigen
FROM dbo.Tarjetas_Resumenes AS rs
INNER JOIN dbo.TarjetasContacto AS tc ON tc.IdTarjeta = rs.IdTarjeta
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = tc.IdContacto
CROSS APPLY (VALUES
        {_VALORES_CARGOS}
    ) AS cg (N, Nombre, Importe)
WHERE ISNULL(rs.EstadoResumen, '') <> 'Cerrado' AND ISNULL(cg.Importe, 0) <> 0
"""

RAMA_DEVOLUCION = """
SELECT
    m.Fecha AS Fecha,
    tc.IdContacto AS IdContacto,
    ct.[Razon Social],
    CAST('Devolución tarjeta' AS varchar(50)) AS Documento,
    CAST(x.IdCruce AS varchar(50)) AS [Nro Documento],
    CAST(x.Importe AS money) AS Deuda,
    CAST(0 AS money) AS Credito,
    CAST('Tarjeta devolución' AS varchar(50)) AS Origen,
    CAST(x.IdCruce AS bigint) AS IdOrigen
FROM dbo.TarjetasCruces AS x
INNER JOIN dbo.TarjetasContacto AS tc ON tc.IdTarjeta = x.IdTarjeta
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = tc.IdContacto
CROSS APPLY (
    SELECT TOP 1 f.Fecha FROM (
        SELECT b.[Fecha / Hora Mov#] AS Fecha FROM dbo.[Movimientos BNA] AS b
        WHERE x.MedioOrigen = 'bna' AND b.IdMovimientoBNA = x.IdMovimientoOrigen
        UNION ALL
        SELECT g.Fecha AS Fecha FROM dbo.[Movimientos Galicia] AS g
        WHERE x.MedioOrigen = 'galicia' AND g.IdMovimiento = x.IdMovimientoOrigen
    ) AS f
) AS m
WHERE x.Tipo = 'devolucion-debito' AND x.Deshecho = 0
"""

RAMA_PAGO_SIN_MOVIMIENTO = """
SELECT
    p.Fecha AS Fecha,
    tc.IdContacto AS IdContacto,
    ct.[Razon Social],
    CAST('Pago tarjeta sin movimiento' AS varchar(50)) AS Documento,
    CAST(rs.ResumenCodigo AS varchar(50)) AS [Nro Documento],
    CAST(0 AS money) AS Deuda,
    CAST(p.Importe AS money) AS Credito,
    CAST('Tarjeta pago' AS varchar(50)) AS Origen,
    CAST(p.IdPago AS bigint) AS IdOrigen
FROM dbo.Tarjetas_Resumenes_Pagos AS p
INNER JOIN dbo.Tarjetas_Resumenes AS rs ON rs.IdResumen = p.IdResumen
INNER JOIN dbo.TarjetasContacto AS tc ON tc.IdTarjeta = rs.IdTarjeta
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = tc.IdContacto
WHERE p.IdMovimientoOrigen IS NULL AND ISNULL(p.Importe, 0) <> 0 AND ISNULL(rs.EstadoResumen, '') <> 'Cerrado'
"""

RAMA_MERCADO_PAGO = """
SELECT
    CAST(m.Fecha AS datetime) AS Fecha,
    m.IdContacto AS IdContacto,
    ct.[Razon Social],
    CAST('Mercado Pago' AS varchar(50)) AS Documento,
    CAST(m.IdOperacion AS varchar(50)) AS [Nro Documento],
    CASE WHEN ISNULL(m.Importe, 0) > 0 THEN CAST(m.Importe AS money) ELSE CAST(0 AS money) END AS Deuda,
    CASE WHEN ISNULL(m.Importe, 0) < 0 THEN CAST(-m.Importe AS money) ELSE CAST(0 AS money) END AS Credito,
    CAST('Mercado Pago' AS varchar(50)) AS Origen,
    CAST(m.IdMovimiento AS bigint) AS IdOrigen
FROM dbo.[Movimientos Mercado Libre] AS m
INNER JOIN dbo.Contactos AS ct ON ct.IdContacto = m.IdContacto
WHERE m.IdContacto IS NOT NULL AND ISNULL(m.Importe, 0) <> 0
  AND NOT EXISTS (SELECT 1 FROM dbo.ConciliacionesTesoreria AS c
                  WHERE c.Medio = 'mercado-libre' AND c.IdMovimiento = m.IdMovimiento)
  AND NOT EXISTS (SELECT 1 FROM dbo.[Movimientos Mercado Libre] AS i
                  WHERE i.IdOperacion = m.IdOperacion AND i.IdMovimiento <> m.IdMovimiento
                    AND i.Descripcion LIKE N'Ingreso de dinero%' AND i.Fecha = m.Fecha
                    AND ABS(i.Importe + m.Importe) < 0.01)
"""

RAMAS = (RAMA_CONSUMO, RAMA_CARGO, RAMA_DEVOLUCION, RAMA_PAGO_SIN_MOVIMIENTO, RAMA_MERCADO_PAGO)
BLOQUE_RAMAS = "".join("\n\nUNION ALL\n" + rama for rama in RAMAS)


# --------------------------------------------------------------------------- utilidades

def _conexion(autocommit: bool = True):
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=autocommit)
    if conn.cursor().execute("SELECT DB_NAME()").fetchone()[0] != "WC":
        conn.close()
        raise RuntimeError("Solo sobre WC")
    return conn


def _definicion_vista(cur) -> str:
    fila = cur.execute(f"SELECT OBJECT_DEFINITION(OBJECT_ID('{VISTA}'))").fetchone()
    if not fila or not fila[0]:
        raise RuntimeError("No se encontró la vista")
    return fila[0].replace("\r\n", "\n")


def _vista_ya_ampliada(definicion: str) -> bool:
    return all(f"'{o}'" in definicion for o in ORIGENES_NUEVOS)


def _definicion_ampliada(definicion: str) -> str:
    if definicion.count(MARCA_FIN) != 1:
        raise RuntimeError("No se encontró el cierre de la unión en la vista.")
    return definicion.replace(MARCA_FIN, BLOQUE_RAMAS + MARCA_FIN).replace("CREATE VIEW", "ALTER VIEW", 1)


def _validar_tarjetas(cur) -> dict[int, int]:
    """Cada tarjeta debe tener un único contacto de tipo tarjeta con su mismo nombre."""
    asignadas: dict[int, int] = {}
    for id_tarjeta, esperado in TARJETAS_ESPERADAS.items():
        filas = cur.execute(
            "SELECT c.IdContacto FROM dbo.Tarjetas t JOIN dbo.Contactos c ON c.[Razon Social] = t.TarjetaNombre "
            "AND c.[Tipo Contacto] = 'Tarjeta de Credito' WHERE t.IdTarjeta = ?", id_tarjeta).fetchall()
        if len(filas) != 1 or filas[0][0] != esperado:
            raise RuntimeError(f"La tarjeta {id_tarjeta} no resuelve al contacto {esperado}: {[f[0] for f in filas]}")
        asignadas[id_tarjeta] = filas[0][0]
    return asignadas


def _crear_tablas_y_mapeo(cur, asignadas: dict[int, int]) -> None:
    cur.execute(DDL_TARJETAS_CONTACTO)
    cur.execute(DDL_TARJETAS_CRUCES)
    cur.execute(DDL_INDICE_CRUCES)
    for id_tarjeta, id_contacto in asignadas.items():
        cur.execute(
            "IF NOT EXISTS (SELECT 1 FROM dbo.TarjetasContacto WHERE IdTarjeta = ?) "
            "INSERT INTO dbo.TarjetasContacto (IdTarjeta, IdContacto, Usuario) VALUES (?, ?, 'migracion-034')",
            id_tarjeta, id_tarjeta, id_contacto)


# --------------------------------------------------------------------------- instantánea

def _saldos(cur) -> dict[str, float]:
    filas = cur.execute(
        f"SELECT IdContacto, CAST(SUM(ISNULL(Credito,0) - ISNULL(Deuda,0)) AS decimal(18,2)) FROM {VISTA} GROUP BY IdContacto"
    ).fetchall()
    return {str(f[0]): float(f[1]) for f in filas}


def _flujo_mensual() -> dict[str, dict[str, float]]:
    """Totales mensuales del flujo de caja real (movimientos bancarios no internos), 2024-01 a 2026-09."""
    from src.features.flujo_caja.repository import get_movimientos_normalizados

    meses: dict[str, dict[str, float]] = defaultdict(lambda: {"ingresos": 0.0, "egresos": 0.0})
    for m in get_movimientos_normalizados(date(2024, 1, 1), date(2026, 9, 30)):
        if m["esInterno"]:
            continue
        f = m["fecha"]
        clave = f"{f.year}-{f.month:02d}"
        meses[clave]["ingresos" if m["importe"] >= 0 else "egresos"] += abs(float(m["importe"]))
    return {k: {c: round(v, 2) for c, v in d.items()} for k, d in sorted(meses.items())}


def _instantanea(cur) -> dict:
    saldos = _saldos(cur)
    return {"fecha": datetime.now().isoformat(timespec="seconds"), "saldos": saldos,
            "total": round(sum(saldos.values()), 2), "flujo": _flujo_mensual()}


def _comparar(antes: dict, ahora: dict, ids_tarjeta: set[int]) -> tuple[list[str], list[str]]:
    """Devuelve (líneas del informe, problemas). Problema = cambio inesperado en un contacto que no es tarjeta."""
    informe, problemas = [], []
    cambios = []
    for contacto in sorted(set(antes["saldos"]) | set(ahora["saldos"]), key=int):
        a, b = antes["saldos"].get(contacto, 0.0), ahora["saldos"].get(contacto, 0.0)
        if abs(b - a) > 0.005:
            cambios.append((int(contacto), a, b))
    tarjetas = [c for c in cambios if c[0] in ids_tarjeta]
    otros = [c for c in cambios if c[0] not in ids_tarjeta]
    for contacto, a, b in tarjetas:
        informe.append(f"  tarjeta {contacto}: {a:,.2f} -> {b:,.2f} (Δ {b - a:,.2f})")
    for contacto, a, b in otros:
        esperado = contacto == CONTACTO_UATRE and abs((b - a) - DIFERENCIA_UATRE) < 0.01
        etiqueta = "esperado (FR-005)" if esperado else "NUEVO/INESPERADO"
        informe.append(f"  contacto {contacto}: {a:,.2f} -> {b:,.2f} (Δ {b - a:,.2f}) {etiqueta}")
        if not esperado and not (contacto not in {int(k) for k in antes["saldos"]} and abs(a) < 0.005):
            problemas.append(f"contacto {contacto}: Δ {b - a:,.2f}")
    informe.append(f"  total general: {antes['total']:,.2f} -> {ahora['total']:,.2f} (Δ {ahora['total'] - antes['total']:,.2f})")
    flujo_igual = antes["flujo"] == ahora["flujo"]
    informe.append(f"  flujo de caja mensual idéntico: {'sí' if flujo_igual else 'NO'}")
    if not flujo_igual:
        problemas.append("el flujo de caja cambió")
    return informe, problemas


# --------------------------------------------------------------------------- modos

def verificar() -> None:
    conn = _conexion()
    try:
        cur = conn.cursor()
        definicion = _definicion_vista(cur)
        print(f"Vista ya ampliada: {_vista_ya_ampliada(definicion)}; cierre de unión único: {definicion.count(MARCA_FIN) == 1}")
        asignadas = _validar_tarjetas(cur)
        print(f"Mapeo tarjeta -> contacto válido: {asignadas}")
        for nombre in ("TarjetasContacto", "TarjetasCruces"):
            existe = cur.execute("SELECT OBJECT_ID(?, 'U')", f"dbo.{nombre}").fetchone()[0] is not None
            print(f"Tabla {nombre}: {'existe' if existe else 'se creará'}")
        existe_tc = cur.execute("SELECT OBJECT_ID('dbo.TarjetasContacto', 'U')").fetchone()[0] is not None
        if existe_tc:
            for etiqueta, rama in (("consumo", RAMA_CONSUMO), ("cargo", RAMA_CARGO)):
                n, imp = cur.execute(f"SELECT COUNT(*), SUM(Deuda - Credito) FROM ({rama}) AS r").fetchone()
                print(f"Rama {etiqueta}: {n} filas, neto de deuda {float(imp or 0):,.2f}")
        else:
            n = cur.execute("SELECT COUNT(*) FROM dbo.Tarjetas_Resumenes_Lineas l JOIN dbo.Tarjetas_Resumenes r "
                            "ON r.IdResumen = l.IdResumen WHERE ISNULL(r.EstadoResumen,'') <> 'Cerrado' AND ISNULL(l.Importe,0) <> 0").fetchone()[0]
            print(f"Rama consumo aportaría {n} filas (la tabla de mapeo aún no existe)")
        n, imp = cur.execute(f"SELECT COUNT(*), SUM(Credito - Deuda) FROM ({RAMA_MERCADO_PAGO}) AS r").fetchone()
        print(f"Rama Mercado Pago: {n} filas, neto a favor {float(imp or 0):,.2f}")
        print("Solo verificación: no se escribió nada.")
    finally:
        conn.close()


def ensayo() -> int:
    """Ejecuta todo en una transacción y la revierte siempre."""
    conn = _conexion(autocommit=False)
    try:
        cur = conn.cursor()
        definicion = _definicion_vista(cur)
        antes = _instantanea(cur)
        asignadas = _validar_tarjetas(cur)
        _crear_tablas_y_mapeo(cur, asignadas)
        if not _vista_ya_ampliada(definicion):
            cur.execute(_definicion_ampliada(definicion))
        ahora = _instantanea(cur)
        informe, problemas = _comparar(antes, ahora, set(asignadas.values()))
        print("ENSAYO (transacción con rollback)\n" + "\n".join(informe))
        print("Problemas:", problemas or "ninguno")
        return 1 if problemas else 0
    finally:
        conn.rollback()
        conn.close()
        print("Rollback hecho: no quedó ningún cambio.")


def aplicar() -> None:
    from src.features.vinculos.backup import backup_verificado

    conn = _conexion()
    try:
        cur = conn.cursor()
        definicion = _definicion_vista(cur)
        asignadas = _validar_tarjetas(cur)
        CARPETA.mkdir(parents=True, exist_ok=True)
        if not ARCHIVO_INSTANTANEA.exists():
            ARCHIVO_INSTANTANEA.write_text(json.dumps(_instantanea(cur), ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"Instantánea previa guardada: {ARCHIVO_INSTANTANEA}")
        else:
            print(f"Ya existía una instantánea previa: {ARCHIVO_INSTANTANEA} (no se sobrescribe)")
        if not ARCHIVO_VISTA_PREVIA.exists() and not _vista_ya_ampliada(definicion):
            ARCHIVO_VISTA_PREVIA.write_text(definicion, encoding="utf-8")
            print(f"Definición previa de la vista guardada: {ARCHIVO_VISTA_PREVIA}")
        print(f"Respaldo verificado: {backup_verificado('cuentas-tarjetas-034')}")
        _crear_tablas_y_mapeo(cur, asignadas)
        if _vista_ya_ampliada(definicion):
            print("La vista ya incluye las ramas de 034.")
        else:
            cur.execute(_definicion_ampliada(definicion))
            print("Vista ampliada con las ramas Tarjeta consumo, Tarjeta cargo, Tarjeta devolución, Tarjeta pago y Mercado Pago.")
    finally:
        conn.close()


def comparar() -> int:
    if not ARCHIVO_INSTANTANEA.exists():
        raise SystemExit("No hay instantánea previa: ejecutá primero el script sin opciones.")
    antes = json.loads(ARCHIVO_INSTANTANEA.read_text(encoding="utf-8"))
    conn = _conexion()
    try:
        cur = conn.cursor()
        ids = {f[0] for f in cur.execute("SELECT IdContacto FROM dbo.TarjetasContacto").fetchall()} | \
              {f[0] for f in cur.execute("SELECT IdContactoAnterior FROM dbo.TarjetasContacto WHERE IdContactoAnterior IS NOT NULL").fetchall()}
        ahora = _instantanea(cur)
    finally:
        conn.close()
    informe, problemas = _comparar(antes, ahora, ids)
    print(f"Comparación contra la instantánea del {antes['fecha']}\n" + "\n".join(informe))
    print("Problemas:", problemas or "ninguno")
    return 1 if problemas else 0


def revertir() -> None:
    if not ARCHIVO_VISTA_PREVIA.exists():
        raise SystemExit("No se encontró la definición previa de la vista.")
    previa = ARCHIVO_VISTA_PREVIA.read_text(encoding="utf-8")
    conn = _conexion()
    try:
        conn.cursor().execute(previa.replace("CREATE VIEW", "ALTER VIEW", 1))
        print("Vista restaurada a su definición previa (las tablas TarjetasContacto y TarjetasCruces quedan).")
    finally:
        conn.close()


def main(argv: list[str]) -> int:
    if "--verificar" in argv:
        verificar()
    elif "--ensayo" in argv:
        return ensayo()
    elif "--comparar" in argv:
        return comparar()
    elif "--revertir" in argv:
        revertir()
    else:
        aplicar()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
