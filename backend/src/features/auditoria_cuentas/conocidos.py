"""Reglas de lo ya conocido: conceptos de movimientos y diferencias de cuentas documentadas — 035 (T019).

Un mismo mecanismo para todas las cuentas y todos los movimientos, sin umbral de importe:

  * `concepto-movimiento`: un movimiento del banco sin contacto cuyo concepto contiene la clave se da por
    explicado (impuestos del banco, fondos propios, ...), de cualquier monto.
  * `cuenta`: Sergio documenta la diferencia de una cuenta con el Access (con su motivo); mientras la diferencia
    siga siendo la documentada deja de contar como excepción, y si cambia vuelve a aparecer.
  * `tc-pactado`: el proveedor factura en dólares a un tipo de cambio pactado (la clave es el contacto): sus pagos
    en pesos se pasan a dólares con el tipo de cambio de las facturas y no con el dólar BNA, sin diferencia de cambio.
  * `cuit-compartido`: varios contactos legítimos comparten un CUIT (por ejemplo las estaciones de una misma operadora, cada una con su
    cuenta): la clave es el CUIT de 11 dígitos y deja de informarse como "contacto duplicado".

Nada se borra: dar de baja una regla la marca inactiva con usuario y fecha.
"""

from __future__ import annotations

from src.db.connection import execute_insert_returning_id, execute_write, fetch_all, fetch_one

TIPOS = ("concepto-movimiento", "cuenta", "tc-pactado", "cuit-compartido")


class ConocidoError(Exception):
    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo


def listar(solo_activos: bool = True) -> list[dict]:
    try:
        return fetch_all(
            "SELECT IdConocido AS idConocido, Tipo AS tipo, Clave AS clave, ImporteRef AS importeRef, Motivo AS motivo, "
            "Usuario AS usuario, Fecha AS fecha, Activo AS activo FROM dbo.AuditoriaConocidos "
            + ("WHERE Activo = 1 " if solo_activos else "") + "ORDER BY IdConocido", ())
    except Exception:
        return []  # sin tabla todavía


def crear(tipo: str, clave: str, motivo: str, importe_ref: float | None, usuario: str) -> dict:
    if tipo not in TIPOS:
        raise ConocidoError(422, "Tipo desconocido")
    clave = (clave or "").strip()
    motivo = (motivo or "").strip()
    if not clave or not motivo:
        raise ConocidoError(422, "Falta la clave o el motivo")
    if tipo == "cuit-compartido":
        clave = "".join(ch for ch in clave if ch.isdigit())
        if len(clave) != 11:
            raise ConocidoError(422, "El CUIT debe tener 11 dígitos")
    elif tipo == "concepto-movimiento":
        clave = clave.upper()
        if len(clave) < 4:
            raise ConocidoError(422, "El concepto es muy corto: tiene que tener al menos 4 caracteres")
    else:
        if not clave.isdigit():
            raise ConocidoError(422, "La cuenta debe ser un número de contacto")
        if tipo == "cuenta" and importe_ref is None:
            raise ConocidoError(422, "Falta la diferencia que se documenta")
    if fetch_one("SELECT 1 AS x FROM dbo.AuditoriaConocidos WHERE Activo = 1 AND Tipo = ? AND Clave = ?", (tipo, clave)):
        raise ConocidoError(409, "Ya existe una regla igual")
    nuevo = execute_insert_returning_id(
        "INSERT INTO dbo.AuditoriaConocidos (Tipo, Clave, ImporteRef, Motivo, Usuario) OUTPUT INSERTED.IdConocido VALUES (?, ?, ?, ?, ?)",
        (tipo, clave, importe_ref, motivo, usuario))
    return {"idConocido": nuevo, "tipo": tipo, "clave": clave, "importeRef": importe_ref, "motivo": motivo, "usuario": usuario, "activo": True}


def dar_de_baja(id_conocido: int, usuario: str) -> None:
    fila = fetch_one("SELECT Activo AS a FROM dbo.AuditoriaConocidos WHERE IdConocido = ?", (id_conocido,))
    if fila is None:
        raise ConocidoError(404, "La regla no existe")
    if not fila["a"]:
        raise ConocidoError(409, "La regla ya estaba dada de baja")
    execute_write("UPDATE dbo.AuditoriaConocidos SET Activo = 0, UsuarioBaja = ?, FechaBaja = SYSDATETIME() WHERE IdConocido = ?",
                  (usuario, id_conocido))
