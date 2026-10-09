"""Marcas de pagos sin factura y saldos externos — 036 (research D12; data-model.md).

Las lecturas no escriben. Las escrituras nunca borran filas, no tocan `LaHerencia` y dejan cada cambio en
`AuditoriaRevisionesHistorial` (existente) con `Accion` `pago-sin-factura`. El sistema no se conecta a ningún portal ni
cuenta externa: los saldos externos los carga una persona.
"""

from __future__ import annotations

import json
import re
from datetime import date

from src.db.connection import execute_write_transaction, fetch_all, fetch_one

ESTADOS_MARCA = ("pendiente", "factura-cargada", "sin-documento", "anticipo", "venta-cargada")
# Una venta (de hacienda o de granos) también respalda un pago de un cliente: la retención o el cobro es parte de esa venta
TIPOS_VENTA = {"venta-hacienda": ("Venta Hacienda", "[Nro documento]", "venta de hacienda"),
               "venta-granos": ("Venta Granos", "[Nro Documento]", "venta de granos")}
FUENTES_RESPALDO = ("portal", "estado-de-cuenta", "pdf")
_EXTENSION_DE_ARCHIVO = re.compile(r"\.(pdf|jpe?g|png|tiff?|crdownload)\b", re.IGNORECASE)


def tiene_archivo(documento_original: str | None) -> bool:
    """Una compra tiene archivo si su "documento original" es una ruta a un comprobante (no un texto de respaldo)."""
    texto = (documento_original or "").strip()
    return bool(texto) and not texto.lower().startswith(("sin archivo", "portal")) and bool(_EXTENSION_DE_ARCHIVO.search(texto))


# --------------------------------------------------------------------------- marcas de pagos sin factura

def validar_marca(id_contacto: int, estado: str, nota: str | None, id_compra: int | None, fuente_respaldo: str | None,
                  tipo_venta: str | None = None, id_venta: int | None = None) -> bool:
    """Valida el pedido de una marca (ValueError si no corresponde) y dice si la factura quedó sin archivo.

    `sin-documento` exige nota. `factura-cargada` exige la fuente de respaldo cuando la factura no tiene archivo o no se
    indica cuál es (FR-020).
    """
    if estado not in ESTADOS_MARCA:
        raise ValueError("Estado desconocido")
    if estado == "sin-documento" and not (nota or "").strip():
        raise ValueError("Falta la nota: explicá por qué no hay documento")
    if fuente_respaldo is not None and fuente_respaldo not in FUENTES_RESPALDO:
        raise ValueError("Fuente de respaldo desconocida")
    if estado == "venta-cargada":
        if tipo_venta not in TIPOS_VENTA or id_venta is None:
            raise ValueError("Indicá cuál venta respalda el pago: de hacienda o de granos, y su número")
        tabla = TIPOS_VENTA[tipo_venta][0]
        if fetch_one(f"SELECT 1 AS x FROM dbo.[{tabla}] WHERE IdVenta = ? AND IdConsignatario = ?", (id_venta, id_contacto)) is None:
            raise ValueError("La venta no existe o no es de esta cuenta")
        return False
    if tipo_venta is not None or id_venta is not None:
        raise ValueError("La venta solo se indica cuando el pago está respaldado por una venta")
    sin_archivo = False
    if estado == "factura-cargada":
        if id_compra is None:
            sin_archivo = True
        else:
            f = fetch_one("SELECT [Documento Original] AS d FROM dbo.Compras WHERE IdDeuda = ? AND IdContacto = ?", (id_compra, id_contacto))
            if f is None:
                raise ValueError("La factura no existe o no es de esta cuenta")
            sin_archivo = not tiene_archivo(f["d"])
        if sin_archivo and fuente_respaldo is None:
            raise ValueError("La factura no tiene archivo: indicá en qué se respalda (portal, estado de cuenta o PDF)")
    return sin_archivo


def texto_de_venta(tipo_venta: str | None, id_venta: int | None) -> str | None:
    """Rótulo legible de la venta que respalda un pago, por ejemplo "venta de hacienda 00003-00000014"."""
    if tipo_venta not in TIPOS_VENTA or id_venta is None:
        return None
    tabla, columna_nro, rotulo = TIPOS_VENTA[tipo_venta]
    fila = fetch_one(f"SELECT {columna_nro} AS n FROM dbo.[{tabla}] WHERE IdVenta = ?", (id_venta,))
    return f"{rotulo} {fila['n']}" if fila and fila["n"] else f"{rotulo} #{id_venta}"


def ventas_de_cuenta(id_contacto: int) -> list[dict]:
    """Ventas de hacienda y de granos de la cuenta, para elegir cuál respalda un pago."""
    salida = []
    for tipo, (tabla, columna_nro, rotulo) in TIPOS_VENTA.items():
        for f in fetch_all(f"SELECT IdVenta AS i, Fecha AS f, {columna_nro} AS n FROM dbo.[{tabla}] WHERE IdConsignatario = ? ORDER BY Fecha DESC", (id_contacto,)):
            salida.append({"tipo": tipo, "idVenta": int(f["i"]), "fecha": f["f"], "numero": f["n"], "rotulo": f"{rotulo} {f['n'] or '#' + str(f['i'])}"})
    return sorted(salida, key=lambda v: str(v["fecha"]), reverse=True)


def leer_marcas(id_contacto: int) -> dict[tuple[str, int], dict]:
    """Marcas vigentes de la cuenta, por (medio, idMovimiento)."""
    filas = fetch_all("SELECT Medio AS medio, IdMovimiento AS mov, Estado AS estado, IdCompra AS compra, FuenteRespaldo AS fuente, Nota AS nota, "
                      "TipoVenta AS tv, IdVenta AS iv FROM dbo.RevisionPagosSinFactura WHERE IdContacto = ?", (id_contacto,))
    return {(f["medio"], int(f["mov"])): {"estado": f["estado"], "nota": f["nota"], "idCompra": f["compra"], "fuenteRespaldo": f["fuente"],
                                          "tipoVenta": f["tv"], "idVenta": f["iv"], "respaldo": texto_de_venta(f["tv"], f["iv"])}
            for f in filas}


def leer_marcas_todas(ids: list[int] | None = None) -> dict[int, dict[tuple[str, int], dict]]:
    """Marcas vigentes de varias cuentas (todas si `ids` es None), por cuenta y (medio, idMovimiento)."""
    filtro, params = ("", ()) if not ids else (" WHERE IdContacto IN (" + ",".join("?" * len(ids)) + ")", tuple(ids))
    filas = fetch_all("SELECT IdContacto AS c, Medio AS medio, IdMovimiento AS mov, Estado AS estado, IdCompra AS compra, FuenteRespaldo AS fuente, Nota AS nota "
                      "FROM dbo.RevisionPagosSinFactura" + filtro, params)
    salida: dict[int, dict] = {}
    for f in filas:
        salida.setdefault(int(f["c"]), {})[(f["medio"], int(f["mov"]))] = {"estado": f["estado"], "nota": f["nota"], "idCompra": f["compra"],
                                                                          "fuenteRespaldo": f["fuente"]}
    return salida


def guardar_marca(id_contacto: int, medio: str, id_movimiento: int, estado: str, id_compra: int | None,
                  fuente_respaldo: str | None, nota: str | None, usuario: str,
                  tipo_venta: str | None = None, id_venta: int | None = None) -> dict:
    """Crea o cambia la marca de un pago sin factura (una sola por movimiento) y deja el cambio en el historial.

    Si la factura queda sin archivo, el "documento original" de la compra dice en qué se respalda (FR-020).
    """
    anterior = leer_marcas(id_contacto).get((medio, id_movimiento))
    nota = (nota or "").strip()[:500] or None
    sin_archivo = validar_marca(id_contacto, estado, nota, id_compra, fuente_respaldo, tipo_venta, id_venta)
    detalle = json.dumps({"medio": medio, "idMovimiento": id_movimiento, "anterior": anterior,
                          "nuevo": {"estado": estado, "idCompra": id_compra, "fuenteRespaldo": fuente_respaldo, "nota": nota, "tipoVenta": tipo_venta, "idVenta": id_venta}},
                         ensure_ascii=False, default=str)
    if anterior is not None:
        marca_sql = ("UPDATE dbo.RevisionPagosSinFactura SET Estado = ?, IdCompra = ?, FuenteRespaldo = ?, Nota = ?, Usuario = ?, TipoVenta = ?, IdVenta = ?, "
                     "Fecha = SYSDATETIME() WHERE IdContacto = ? AND Medio = ? AND IdMovimiento = ?",
                     (estado, id_compra, fuente_respaldo, nota, usuario, tipo_venta, id_venta, id_contacto, medio, id_movimiento))
    else:
        marca_sql = ("INSERT INTO dbo.RevisionPagosSinFactura (IdContacto, Medio, IdMovimiento, Estado, IdCompra, FuenteRespaldo, Nota, Usuario, TipoVenta, IdVenta) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (id_contacto, medio, id_movimiento, estado, id_compra, fuente_respaldo, nota, usuario, tipo_venta, id_venta))
    operaciones: list = [
        marca_sql,
        ("INSERT INTO dbo.AuditoriaRevisionesHistorial (IdContacto, Accion, Detalle, Usuario) VALUES (?, 'pago-sin-factura', ?, ?)",
         (id_contacto, detalle, usuario)),
    ]
    if estado == "factura-cargada" and id_compra is not None and sin_archivo:
        operaciones.append((
            "UPDATE dbo.Compras SET [Documento Original] = ? WHERE IdDeuda = ? AND IdContacto = ?",
            (f"Sin archivo, respaldo: {fuente_respaldo} {date.today().strftime('%d/%m/%Y')}", id_compra, id_contacto)))
    execute_write_transaction(operaciones)
    from src.features.revision_cuentas import cache

    cache.invalidar()
    return {"estado": estado, "nota": nota, "idCompra": id_compra, "fuenteRespaldo": fuente_respaldo,
            "tipoVenta": tipo_venta, "idVenta": id_venta, "respaldo": texto_de_venta(tipo_venta, id_venta)}


# --------------------------------------------------------------------------- saldos externos (RevisionSaldosExternos)

FUENTES_SALDO = ("portal", "pdf", "mail", "banco", "tarjeta", "sin-estado")
TOLERANCIA_REDONDEO = 1.0           # una diferencia de redondeo se da por igual
UMBRAL_PESOS = 300.0                # una diferencia menor se da por cerrada (solo en pesos)
TOLERANCIA_RELATIVA_DOLARES = 0.005  # en dólares rige una tolerancia relativa, nunca un monto fijo


def clasificar_saldo_externo(saldo_externo: float, saldo_cuenta: float, moneda: str, umbral_pesos: float = UMBRAL_PESOS) -> tuple[float, str]:
    """Diferencia (saldo de la cuenta menos saldo externo) y su clasificación: `cierra`, `menor-al-umbral` o `con-diferencia`.

    Ambos saldos van con el mismo signo (positivo a favor nuestro). En pesos: hasta $1 cierra y hasta el umbral ($300) es menor al umbral.
    En dólares solo hay tolerancia relativa (0,5 %): nunca se aplica un monto fijo.
    """
    diferencia = round(saldo_cuenta - saldo_externo, 2)
    if moneda == "Dolares":
        base = max(abs(saldo_externo), abs(saldo_cuenta), 1.0)
        return diferencia, ("cierra" if abs(diferencia) <= TOLERANCIA_RELATIVA_DOLARES * base else "con-diferencia")
    if abs(diferencia) <= TOLERANCIA_REDONDEO:
        return diferencia, "cierra"
    return diferencia, ("menor-al-umbral" if abs(diferencia) <= umbral_pesos else "con-diferencia")


def _a_fecha(valor) -> date:
    from datetime import datetime
    if isinstance(valor, datetime):
        return valor.date()
    return date.fromisoformat(valor[:10]) if isinstance(valor, str) else valor


def listar_saldos_externos(id_contacto: int, saldo_a_la_fecha, umbral_pesos: float = UMBRAL_PESOS) -> list[dict]:
    """Saldos externos vigentes de la cuenta (del más nuevo al más viejo) con su diferencia contra el saldo de la cuenta a esa fecha.

    `saldo_a_la_fecha(fecha) -> float` da el saldo de la cuenta en esa fecha (se inyecta para poder probar sin base).
    """
    filas = fetch_all(
        "SELECT IdSaldoExterno AS id, FechaSaldo AS fecha, Saldo AS saldo, Moneda AS moneda, Fuente AS fuente, Referencia AS ref, Nota AS nota "
        "FROM dbo.RevisionSaldosExternos WHERE IdContacto = ? AND Anulado = 0 ORDER BY FechaSaldo DESC, IdSaldoExterno DESC", (id_contacto,))
    salida = []
    for f in filas:
        fecha, saldo = _a_fecha(f["fecha"]), round(float(f["saldo"]), 2)
        saldo_cuenta = round(float(saldo_a_la_fecha(fecha)), 2)
        if f["fuente"] == "sin-estado":
            diferencia, clasificacion = 0.0, "cierra"
        else:
            diferencia, clasificacion = clasificar_saldo_externo(saldo, saldo_cuenta, f["moneda"], umbral_pesos)
        salida.append({"idSaldoExterno": int(f["id"]), "fechaSaldo": fecha, "saldo": saldo, "moneda": f["moneda"], "fuente": f["fuente"],
                       "referencia": f["ref"], "nota": f["nota"], "saldoCuentaALaFecha": saldo_cuenta, "diferencia": diferencia,
                       "clasificacion": clasificacion})
    return salida


def validar_saldo_externo(fecha_saldo: date, fuente: str, nota: str | None, moneda: str) -> None:
    """Valida el alta de un saldo externo (ValueError → 422): fecha no futura, fuente conocida y nota obligatoria si no hay estado de cuenta."""
    if fecha_saldo > date.today():
        raise ValueError("La fecha del saldo no puede ser futura")
    if fuente not in FUENTES_SALDO:
        raise ValueError("Fuente desconocida")
    if moneda not in ("Pesos", "Dolares"):
        raise ValueError("Moneda desconocida")
    if fuente == "sin-estado" and not (nota or "").strip():
        raise ValueError("Anotá por qué no se pide el estado de cuenta (por ejemplo, movimientos viejos o proveedor sin portal)")


def crear_saldo_externo(id_contacto: int, fecha_saldo: date, saldo: float, moneda: str, fuente: str, referencia: str | None, nota: str | None, usuario: str) -> int:
    """Registra un saldo externo (lo carga una persona; el sistema no busca saldos por su cuenta) y deja el alta en el historial."""
    nota = (nota or "").strip()[:500] or None
    referencia = (referencia or "").strip()[:400] or None
    validar_saldo_externo(fecha_saldo, fuente, nota, moneda)
    detalle = json.dumps({"fechaSaldo": str(fecha_saldo), "saldo": saldo, "moneda": moneda, "fuente": fuente, "referencia": referencia, "nota": nota}, ensure_ascii=False)
    resultados = execute_write_transaction([
        ("INSERT INTO dbo.RevisionSaldosExternos (IdContacto, FechaSaldo, Saldo, Moneda, Fuente, Referencia, Nota, Usuario) OUTPUT INSERTED.IdSaldoExterno "
         "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (id_contacto, fecha_saldo, saldo, moneda, fuente, referencia, nota, usuario)),
        ("INSERT INTO dbo.AuditoriaRevisionesHistorial (IdContacto, Accion, Detalle, Usuario) VALUES (?, 'saldo-externo', ?, ?)", (id_contacto, detalle, usuario)),
    ])
    from src.features.revision_cuentas import cache

    cache.invalidar()
    return int(resultados[0])


def anular_saldo_externo(id_contacto: int, id_saldo_externo: int, usuario: str) -> bool:
    """Baja lógica de un saldo externo (`Anulado = 1`): nunca se borra la fila. False si no existe o es de otra cuenta."""
    f = fetch_one("SELECT 1 AS x FROM dbo.RevisionSaldosExternos WHERE IdSaldoExterno = ? AND IdContacto = ? AND Anulado = 0", (id_saldo_externo, id_contacto))
    if f is None:
        return False
    execute_write_transaction([
        ("UPDATE dbo.RevisionSaldosExternos SET Anulado = 1 WHERE IdSaldoExterno = ? AND IdContacto = ?", (id_saldo_externo, id_contacto)),
        ("INSERT INTO dbo.AuditoriaRevisionesHistorial (IdContacto, Accion, Detalle, Usuario) VALUES (?, 'saldo-externo', ?, ?)",
         (id_contacto, json.dumps({"anulado": id_saldo_externo}), usuario)),
    ])
    from src.features.revision_cuentas import cache

    cache.invalidar()
    return True
