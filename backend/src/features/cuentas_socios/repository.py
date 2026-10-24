"""Cuentas corrientes de socios/directores y condominio (021).

`MovimientosCuentaSocio` es inmutable: se inserta o se anula, nunca se
edita (spec FR-006, mismo patrón que `AplicacionesPago` en 019). El saldo
de un socio se calcula siempre en el momento (`SUM` sobre vigentes), nunca
se guarda como campo fijo. Cada asignación/reversión/devolución queda
además registrada en `AuditoriaReflejoSocio` (tabla dedicada, decisión
explícita del usuario 2026-09-24 — no el patrón liviano de otras
features).
"""

from __future__ import annotations

from datetime import date

from src.db.connection import execute_write_transaction, fetch_all, fetch_one
from src.features.compras.particular import APLICA_PARTICULAR_JOIN, importe_personal_compra_particular

TOLERANCIA_REDONDEO = 1.0


def _f(value) -> float:
    return float(value) if value is not None else 0.0


def listar_compras_particulares_candidatas(proveedor: str | None = None) -> list[dict]:
    """Compras "particular" (research.md §3) sin asignación vigente a
    ningún socio — candidatas para `asignar_gasto`. `importePersonal` es
    el valor absoluto de la línea negativa (lo que se le asignaría al
    socio), no el total reconstruido — puede ser menor al importe de la
    compra cuando el descuento fue parcial (split, 2026-09-26)."""
    where = ["1 = 1"]
    params: list = []
    if proveedor:
        where.append("ct.[Razon Social] LIKE ?")
        params.append(f"%{proveedor.strip()}%")

    sql = f"""
        SELECT w.IdDeuda AS idCompra, w.Fecha AS fecha, ct.[Razon Social] AS proveedor,
               w.[Nro Documento] AS numeroDocumento, ABS(pa.cp) AS importePersonal
        FROM dbo.vw_Compras_ImporteDocumento w
        {APLICA_PARTICULAR_JOIN}
        JOIN dbo.Contactos ct ON ct.IdContacto = w.IdContacto
        WHERE {' AND '.join(where)}
          AND pa.cp <> 0
          AND NOT EXISTS (
              SELECT 1 FROM dbo.MovimientosCuentaSocio m
              WHERE m.Origen = 'CompraParticular' AND m.IdOrigen = w.IdDeuda
                AND m.Tipo = 'AsignacionGasto' AND m.Anulada = 0
          )
        ORDER BY w.Fecha DESC
    """
    filas = fetch_all(sql, tuple(params))
    return [{**f, "importePersonal": round(_f(f["importePersonal"]), 2)} for f in filas]


def _tiene_asignacion_vigente(id_compra: int) -> bool:
    fila = fetch_one(
        "SELECT 1 AS x FROM dbo.MovimientosCuentaSocio "
        "WHERE Origen = 'CompraParticular' AND IdOrigen = ? AND Tipo = 'AsignacionGasto' AND Anulada = 0",
        (id_compra,),
    )
    return fila is not None


def asignar_gasto(id_socio: int, id_compra: int, usuario: str, motivo: str | None = None) -> dict:
    """Asigna una compra particular a un socio (spec FR-002/FR-003).
    Rechaza si ya tiene una asignación vigente (FR-009) — el índice único
    filtrado en base es la garantía final, esto es el mensaje legible
    antes de llegar ahí."""
    if _tiene_asignacion_vigente(id_compra):
        raise ValueError(f"La compra {id_compra} ya tiene una asignación vigente a un socio.")

    importe = importe_personal_compra_particular(id_compra)
    if importe is None:
        raise ValueError(f"La compra {id_compra} no es una compra particular (no tiene línea negativa 'particular').")

    # Bug real encontrado 2026-09-30 (al migrar Cajas Giamigli, 027): sin
    # `Fecha` explícita en el INSERT, la columna caía en su default
    # (SYSUTCDATETIME — el momento en que se corre este código), no la
    # fecha real de la compra. Se usa acá la fecha de la compra, igual
    # que cualquier otro movimiento con origen real.
    compra = fetch_one("SELECT Fecha FROM dbo.Compras WHERE IdDeuda = ?", (id_compra,))
    fecha_compra = compra["Fecha"] if compra else None

    resultados = execute_write_transaction(
        [
            (
                "INSERT INTO dbo.MovimientosCuentaSocio "
                "(IdSocio, Tipo, Importe, Fecha, Origen, IdOrigen, Motivo, Usuario) "
                "OUTPUT INSERTED.IdMovimiento "
                "VALUES (?, 'AsignacionGasto', ?, ?, 'CompraParticular', ?, ?, ?)",
                (id_socio, importe, fecha_compra, id_compra, motivo, usuario),
            ),
            lambda resultados: (
                "INSERT INTO dbo.AuditoriaReflejoSocio (Accion, IdMovimiento, IdSocio, Usuario, Detalle) "
                "VALUES ('Asignacion', ?, ?, ?, ?)",
                (resultados[0], id_socio, usuario, f"Compra particular #{id_compra}"),
            ),
        ]
    )
    return _movimiento_por_id(resultados[0])


def _movimiento_por_id(id_movimiento: int) -> dict:
    fila = fetch_one(
        "SELECT IdMovimiento AS idMovimiento, IdSocio AS idSocio, Tipo AS tipo, Importe AS importe, "
        "ImporteUSD AS importeUSD, ImporteKgCarne AS importeKgCarne, "
        "Fecha AS fecha, Origen AS origen, IdOrigen AS idOrigen, Medio AS medio, Motivo AS motivo, "
        "Usuario AS usuario, Anulada AS anulada, MotivoAnulacion AS motivoAnulacion "
        "FROM dbo.MovimientosCuentaSocio WHERE IdMovimiento = ?",
        (id_movimiento,),
    )
    assert fila is not None
    return {**fila, "importe": _f(fila["importe"]), "importeUSD": _f(fila["importeUSD"]), "importeKgCarne": _f(fila["importeKgCarne"])}


def anular_movimiento(id_movimiento: int, motivo: str, usuario: str) -> dict:
    """Anulación no destructiva (spec FR-006): nunca `UPDATE`/`DELETE` del
    importe/tipo/origen — solo se marca `Anulada`. Registra en
    `AuditoriaReflejoSocio` la reversión correspondiente según el `Tipo`
    del movimiento anulado."""
    movimiento = fetch_one(
        "SELECT IdMovimiento AS idMovimiento, IdSocio AS idSocio, Tipo AS tipo, Anulada AS anulada "
        "FROM dbo.MovimientosCuentaSocio WHERE IdMovimiento = ?",
        (id_movimiento,),
    )
    if movimiento is None:
        raise ValueError(f"El movimiento {id_movimiento} no existe.")
    if movimiento["anulada"]:
        raise ValueError(f"El movimiento {id_movimiento} ya está anulado.")
    operacion = _operacion_caja(id_movimiento)
    if operacion:
        raise ValueError(f"El movimiento viene de la operación de caja {operacion}: anulala desde la caja para revertir todo junto.")

    accion = "ReversionAsignacion" if movimiento["tipo"] == "AsignacionGasto" else "ReversionDevolucion"
    execute_write_transaction(
        [
            (
                "UPDATE dbo.MovimientosCuentaSocio SET Anulada = 1, MotivoAnulacion = ?, "
                "UsuarioAnulacion = ?, FechaAnulacion = SYSUTCDATETIME() WHERE IdMovimiento = ?",
                (motivo, usuario, id_movimiento),
            ),
            (
                "INSERT INTO dbo.AuditoriaReflejoSocio (Accion, IdMovimiento, IdSocio, Usuario, Detalle) "
                "VALUES (?, ?, ?, ?, ?)",
                (accion, id_movimiento, movimiento["idSocio"], usuario, motivo),
            ),
        ]
    )
    return _movimiento_por_id(id_movimiento)


def calcular_saldo(id_socio: int) -> dict:
    """Saldo del socio en las 3 monedas/unidades de la planilla "Cajas
    Giamigli.xlsx" (027-migracion-cajas-giamigli), sin ninguna conversión
    entre ellas (spec 027, Clarifications) — cada una se suma por
    separado."""
    fila = fetch_one(
        "SELECT "
        "SUM(CASE WHEN Tipo = 'AsignacionGasto' THEN Importe ELSE -Importe END) AS saldoPesos, "
        "SUM(CASE WHEN Tipo = 'AsignacionGasto' THEN ImporteUSD ELSE -ImporteUSD END) AS saldoUSD, "
        "SUM(CASE WHEN Tipo = 'AsignacionGasto' THEN ImporteKgCarne ELSE -ImporteKgCarne END) AS saldoKgCarne "
        "FROM dbo.MovimientosCuentaSocio WHERE IdSocio = ? AND Anulada = 0",
        (id_socio,),
    )
    return {
        "saldoPesos": round(_f(fila["saldoPesos"] if fila else None), 2),
        "saldoUSD": round(_f(fila["saldoUSD"] if fila else None), 2),
        "saldoKgCarne": round(_f(fila["saldoKgCarne"] if fila else None), 2),
    }


ORIGEN_MUTUO = "Mutuo2018"


def cotizaciones_actuales() -> dict:
    """Última cotización disponible de las tablas de WC (036, 22/10/2026; desde 039 el índice es el INMAG):
    INMAG (Mercado Agroganadero) y Dólar BNA billete promedio — las
    mismas que usa la planilla Cajas Giamigli para la "Deuda Actualizada"."""
    nov = fetch_one("SELECT TOP 1 Fecha AS fecha, Indice AS valor FROM dbo.IndiceINMAG ORDER BY Fecha DESC")
    dol = fetch_one("SELECT TOP 1 Fecha AS fecha, Prom_billete AS valor FROM dbo.[Dolar BNA] WHERE Prom_billete IS NOT NULL ORDER BY Fecha DESC")
    return {
        "novillo": _f(nov["valor"]) if nov else 0.0,
        "fechaNovillo": nov["fecha"] if nov else None,
        "dolar": _f(dol["valor"]) if dol else 0.0,
        "fechaDolar": dol["fecha"] if dol else None,
    }


def deuda_actualizada(id_socio: int, cot: dict | None = None) -> dict:
    """Deuda actualizada como la planilla: kg × índice novillo + US$ × dólar
    de hoy (50% kg / 50% US$; 100% US$ antes del 16/03/2020). El mutuo en
    dólares (Lucy 2018) va aparte, solo en US$. Positivo: el socio le debe a
    la empresa; negativo: a favor del socio."""
    cot = cot or cotizaciones_actuales()
    fila = fetch_one(
        "SELECT "
        "SUM(CASE WHEN ISNULL(Origen,'') <> ? THEN (CASE WHEN Tipo = 'AsignacionGasto' THEN 1 ELSE -1 END) * ImporteKgCarne ELSE 0 END) AS kg, "
        "SUM(CASE WHEN ISNULL(Origen,'') <> ? THEN (CASE WHEN Tipo = 'AsignacionGasto' THEN 1 ELSE -1 END) * ImporteUSD ELSE 0 END) AS usd, "
        "SUM(CASE WHEN ISNULL(Origen,'') = ? THEN (CASE WHEN Tipo = 'AsignacionGasto' THEN 1 ELSE -1 END) * ImporteUSD ELSE 0 END) AS mutuo "
        "FROM dbo.MovimientosCuentaSocio WHERE IdSocio = ? AND Anulada = 0",
        (ORIGEN_MUTUO, ORIGEN_MUTUO, ORIGEN_MUTUO, id_socio),
    )
    kg, usd, mutuo = (_f(fila[k]) if fila else 0.0 for k in ("kg", "usd", "mutuo"))
    valor_kg, valor_usd = kg * cot["novillo"], usd * cot["dolar"]
    return {
        "kgCarne": round(kg, 2),
        "dolares": round(usd, 2),
        "valorKgCarne": round(valor_kg, 2),
        "valorDolares": round(valor_usd, 2),
        "deudaActualizada": round(valor_kg + valor_usd, 2),
        "mutuoUSD": round(mutuo, 2),
        "mutuoPesos": round(mutuo * cot["dolar"], 2),
        **cot,
    }


def listar_socios_con_saldo() -> list[dict]:
    """Listado general (GET /api/cuentas-socios): saldo en pesos históricos
    y deuda actualizada (kg × novillo + US$ × dólar de hoy, mutuo aparte)."""
    socios = fetch_all("SELECT IdSocio AS idSocio, Nombre AS nombre FROM dbo.Socios ORDER BY IdSocio")
    cot = cotizaciones_actuales()
    return [{**s, "saldo": calcular_saldo(s["idSocio"])["saldoPesos"], "actualizada": deuda_actualizada(s["idSocio"], cot)} for s in socios]


def listar_movimientos(id_socio: int) -> list[dict]:
    """Movimientos de un socio, incluidos los anulados (nunca se ocultan,
    FR-005/FR-006). Cada `AsignacionGasto` trae el proveedor/documento de
    origen si la compra sigue existiendo, y se marca `huerfano` si no
    (FR-011) — nunca desaparece del historial ni se recalcula como válido."""
    filas = fetch_all(
        """
        SELECT m.IdMovimiento AS idMovimiento, m.Tipo AS tipo, m.Importe AS importe,
               m.ImporteUSD AS importeUSD, m.ImporteKgCarne AS importeKgCarne, m.Fecha AS fecha,
               m.Origen AS origen, m.IdOrigen AS idOrigen, m.Medio AS medio, m.Motivo AS motivo,
               m.Usuario AS usuario, m.Anulada AS anulada, m.MotivoAnulacion AS motivoAnulacion,
               ct.[Razon Social] AS proveedorOrigen, c.[Nro Documento] AS numeroDocumentoOrigen,
               CASE WHEN m.Origen IS NOT NULL AND c.IdDeuda IS NULL THEN 1 ELSE 0 END AS huerfano
        FROM dbo.MovimientosCuentaSocio m
        LEFT JOIN dbo.Compras c ON m.Origen = 'CompraParticular' AND c.IdDeuda = m.IdOrigen
        LEFT JOIN dbo.Contactos ct ON ct.IdContacto = c.IdContacto
        WHERE m.IdSocio = ?
        ORDER BY m.Fecha ASC, m.IdMovimiento ASC
        """,
        (id_socio,),
    )
    ops = _operaciones_caja_socios()
    out = []
    for f in filas:
        m = {**f, "importe": _f(f["importe"]), "importeUSD": _f(f["importeUSD"]), "importeKgCarne": _f(f["importeKgCarne"]),
             "huerfano": bool(f["huerfano"]), "idOperacionCaja": ops.get(f["idMovimiento"])}
        m["editable"] = editable(m)
        out.append(m)
    return out


def registrar_devolucion(id_socio: int, importe: float, fecha: date, medio: str, motivo: str, usuario: str) -> dict:
    """Devolución/compensación manual (spec FR-008). Se acepta aunque
    supere el saldo deudor actual (Edge Case de la spec: el socio puede
    quedar con saldo a favor, no se rechaza)."""
    if importe <= 0:
        raise ValueError("El importe de la devolución debe ser mayor a $0.")
    if not motivo or not motivo.strip():
        raise ValueError("El motivo es obligatorio para registrar una devolución.")

    resultados = execute_write_transaction(
        [
            (
                "INSERT INTO dbo.MovimientosCuentaSocio (IdSocio, Tipo, Importe, Fecha, Medio, Motivo, Usuario) "
                "OUTPUT INSERTED.IdMovimiento "
                "VALUES (?, 'Devolucion', ?, ?, ?, ?, ?)",
                (id_socio, importe, fecha, medio, motivo, usuario),
            ),
            lambda resultados: (
                "INSERT INTO dbo.AuditoriaReflejoSocio (Accion, IdMovimiento, IdSocio, Usuario, Detalle) "
                "VALUES ('Devolucion', ?, ?, ?, ?)",
                (resultados[0], id_socio, usuario, motivo),
            ),
        ]
    )
    return _movimiento_por_id(resultados[0])


# --- Asientos manuales y edición (pedido de Sergio 23/10/2026) -----------------------------------------
# Debe = el socio le debe a la empresa (Tipo AsignacionGasto); Haber = a favor del socio (Tipo Devolucion).
# Se valúan en kg de novillo (INMAG) / US$ a la fecha con la regla histórica, como la planilla.
# Los movimientos generados por una operación de caja (038) o por una compra particular se corrigen
# desde su origen: aquí no se editan ni se anulan sueltos.

ORIGEN_MANUAL = "Manual"


def _operacion_caja(id_movimiento: int) -> int | None:
    fila = fetch_one(
        "SELECT TOP 1 e.IdOperacion AS id FROM dbo.EfectosOperacionCaja e JOIN dbo.OperacionesCajaEfectivo o "
        "ON o.IdOperacion = e.IdOperacion WHERE e.TipoEfecto = 'MovimientoSocio' AND e.IdRegistro = ? AND o.Estado = 'Vigente'",
        (id_movimiento,),
    )
    return fila["id"] if fila else None


def editable(movimiento: dict) -> bool:
    return not movimiento.get("anulada") and movimiento.get("origen") in (None, ORIGEN_MANUAL) and not movimiento.get("idOperacionCaja")


def _insert_asiento(id_socio: int, lado: str, importe: float, fecha: date, medio: str | None, motivo: str, usuario: str):
    from src.features.cuentas_socios.valuacion import a_fecha

    if lado not in ("debe", "haber"):
        raise ValueError("Elegí Debe (el socio debe) o Haber (a favor del socio).")
    if importe <= 0:
        raise ValueError("El importe debe ser mayor a $0.")
    if not motivo or not motivo.strip():
        raise ValueError("El concepto es obligatorio.")
    if not fetch_one("SELECT 1 AS x FROM dbo.Socios WHERE IdSocio = ?", (id_socio,)):
        raise ValueError(f"El socio {id_socio} no existe.")
    v = a_fecha(importe, fecha)
    # US$ y kg se guardan siempre positivos: el Tipo da el signo (calcular_saldo / deuda_actualizada).
    tipo = "AsignacionGasto" if lado == "debe" else "Devolucion"
    return (
        "INSERT INTO dbo.MovimientosCuentaSocio (IdSocio, Tipo, Importe, ImporteUSD, ImporteKgCarne, Fecha, Origen, Medio, Motivo, Usuario) "
        "OUTPUT INSERTED.IdMovimiento VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (id_socio, tipo, importe, float(v["importeUSD"]), float(v["importeKgCarne"]), fecha, ORIGEN_MANUAL,
         medio, motivo.strip(), usuario),
    )


def registrar_asiento(id_socio: int, lado: str, importe: float, fecha: date, medio: str | None, motivo: str, usuario: str) -> dict:
    sql = _insert_asiento(id_socio, lado, importe, fecha, medio, motivo, usuario)
    res = execute_write_transaction([
        sql,
        lambda r: ("INSERT INTO dbo.AuditoriaReflejoSocio (Accion, IdMovimiento, IdSocio, Usuario, Detalle) VALUES (?, ?, ?, ?, ?)",
                   ("AsientoManual", r[0], id_socio, usuario, motivo)),
    ])
    return _movimiento_por_id(res[0])


def editar_asiento(id_movimiento: int, lado: str, importe: float, fecha: date, medio: str | None, motivo: str, usuario: str) -> dict:
    """Editar = anular el asiento anterior y crear el corregido en una transacción: el historial queda completo."""
    actual = _movimiento_por_id(id_movimiento)
    actual["idOperacionCaja"] = _operacion_caja(id_movimiento)
    if not editable(actual):
        raise ValueError("Este movimiento viene de una caja o de una compra: corregilo desde su origen.")
    sql = _insert_asiento(actual["idSocio"], lado, importe, fecha, medio, motivo, usuario)
    res = execute_write_transaction([
        ("UPDATE dbo.MovimientosCuentaSocio SET Anulada = 1, MotivoAnulacion = ?, UsuarioAnulacion = ?, "
         "FechaAnulacion = SYSUTCDATETIME() WHERE IdMovimiento = ? AND Anulada = 0",
         ("Corregido por edición", usuario, id_movimiento)),
        sql,
        lambda r: ("INSERT INTO dbo.AuditoriaReflejoSocio (Accion, IdMovimiento, IdSocio, Usuario, Detalle) VALUES (?, ?, ?, ?, ?)",
                   ("EdicionAsiento", r[1], actual["idSocio"], usuario, f"Reemplaza al movimiento {id_movimiento}: {motivo}")),
    ])
    if res[0] != 1:
        raise ValueError("El movimiento ya fue anulado o modificado por otra persona.")
    return _movimiento_por_id(res[1])


def _operaciones_caja_socios() -> dict[int, int]:
    """IdMovimiento de socio -> operación de caja vigente que lo generó (038)."""
    return {r["IdRegistro"]: r["IdOperacion"] for r in fetch_all(
        "SELECT e.IdRegistro, e.IdOperacion FROM dbo.EfectosOperacionCaja e JOIN dbo.OperacionesCajaEfectivo o "
        "ON o.IdOperacion = e.IdOperacion WHERE e.TipoEfecto = 'MovimientoSocio' AND o.Estado = 'Vigente'")}
