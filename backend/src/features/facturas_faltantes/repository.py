"""044 — Lecturas en bloque y escrituras de las tablas propias del detector (nunca tablas contables)."""

from __future__ import annotations

from src.db.connection import execute_write, execute_write_transaction, fetch_all

# Socios, cuenta sin contacto: no son proveedores (memoria: cuenta de socio = oficial).
EXCLUIDOS = (0, 375, 390, 549, 5670)
# vw_MovimientosCuenta_Saldo.Origen → OrigenMovimiento de AplicacionesPago (pagos que pueden quedar sin factura).
MEDIOS = {"Galicia": "galicia", "Banco Nacion": "bna", "Pagos efectivo": "efectivo"}


def proveedores() -> dict[int, str]:
    filas = fetch_all(
        "SELECT DISTINCT c.IdContacto AS id, ct.[Razon Social] AS nombre FROM dbo.Compras c "
        "JOIN dbo.Contactos ct ON ct.IdContacto = c.IdContacto "
        "WHERE ct.[Razon Social] NOT LIKE '%San Justo%'")
    return {f["id"]: f["nombre"] for f in filas if f["id"] not in EXCLUIDOS}


def comprobantes() -> list[dict]:
    return fetch_all(
        "SELECT c.IdDeuda AS idDeuda, c.IdContacto AS idContacto, c.Fecha AS fecha, c.[Tipo documento] AS tipo, "
        "c.[Nro Documento] AS numero, ABS(v.ImporteDocumento) * CASE WHEN c.Moneda = 'Dolares' THEN c.[Tipo de Cambio] ELSE 1 END AS importe "
        "FROM dbo.Compras c JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda WHERE c.Fecha IS NOT NULL")


def pagos() -> list[dict]:
    origenes = ",".join(f"'{o}'" for o in MEDIOS)
    return fetch_all(
        "SELECT IdContacto AS idContacto, Fecha AS fecha, Origen AS origen, IdOrigen AS idOrigen, Credito AS importe "
        f"FROM dbo.vw_MovimientosCuenta_Saldo WHERE Origen IN ({origenes}) AND Credito > 0")


def fechas_de_deuda() -> list[dict]:
    """Cualquier comprobante de deuda del contacto (compras, boletas de impuestos, sueldos...): basta para no alarmar un pago."""
    return fetch_all("SELECT DISTINCT IdContacto AS idContacto, Fecha AS fecha FROM dbo.vw_MovimientosCuenta_Saldo WHERE Deuda > 0")


def pagos_aplicados() -> set[tuple[str, int]]:
    return {(f["o"], f["i"]) for f in fetch_all(
        "SELECT DISTINCT OrigenMovimiento AS o, IdMovimientoOrigen AS i FROM dbo.AplicacionesPago WHERE Anulada = 0")}


def saldos() -> list[dict]:
    return fetch_all("SELECT IdContacto AS idContacto, ROUND(SUM(Credito - Deuda), 2) AS saldo, MAX(Fecha) AS ultima "
                     "FROM dbo.vw_MovimientosCuenta_Saldo GROUP BY IdContacto")


def retenciones() -> list[dict]:
    return fetch_all("SELECT IdRetencionSQL AS id, IdContacto AS idContacto, Fecha AS fecha, Importe AS importe, "
                     "[Numero Certificado] AS numero FROM dbo.Retenciones")


def remitos_sin_factura() -> list[dict]:
    return fetch_all(
        "SELECT r.IdRemito AS id, r.IdContacto AS idContacto, r.Fecha AS fecha, r.NroRemito AS numero FROM dbo.Remitos r "
        "WHERE NOT EXISTS (SELECT 1 FROM dbo.Remitos_Facturas f WHERE f.IdRemito = r.IdRemito) AND r.Fecha IS NOT NULL")


def perfiles() -> dict[int, dict]:
    return {f["IdContacto"]: f for f in fetch_all("SELECT * FROM dbo.FacturasFaltantesPerfil")}


def descartadas() -> set[str]:
    return {f["Clave"] for f in fetch_all("SELECT Clave FROM dbo.FacturasFaltantesAlarmas")}


def marcas(estado: str | None = None) -> list[dict]:
    w, p = ("WHERE Estado = ?", (estado,)) if estado else ("", ())
    return fetch_all(
        "SELECT IdMarca AS idMarca, IdContacto AS idContacto, OrigenPago AS origenPago, IdPago AS idPago, PeriodoDesde AS periodoDesde, "
        "PeriodoHasta AS periodoHasta, ImporteAprox AS importeAprox, Estado AS estado, IdDeudaCierre AS idDeudaCierre, "
        f"Usuario AS usuario, FechaAlta AS fechaAlta, FechaCierre AS fechaCierre FROM dbo.FacturasFaltantesMarcas {w} ORDER BY FechaAlta DESC", p)


def descartar(clave: str, id_contacto: int, motivo: str, usuario: str) -> None:
    execute_write("INSERT INTO dbo.FacturasFaltantesAlarmas (Clave, IdContacto, Decision, Motivo, Usuario) VALUES (?, ?, 'descartada', ?, ?)",
                  (clave, id_contacto, motivo, usuario))


def crear_marca(d: dict, usuario: str) -> int:
    return execute_write_transaction([(
        "INSERT INTO dbo.FacturasFaltantesMarcas (IdContacto, OrigenPago, IdPago, PeriodoDesde, PeriodoHasta, ImporteAprox, Estado, Usuario) "
        "OUTPUT INSERTED.IdMarca VALUES (?, ?, ?, ?, ?, ?, 'abierta', ?)",
        (d["idContacto"], d["origenPago"], d["idPago"], d.get("periodoDesde"), d.get("periodoHasta"), d.get("importeAprox"), usuario))])[0]


def anular_marca(id_marca: int, motivo: str, usuario: str) -> int:
    return execute_write("UPDATE dbo.FacturasFaltantesMarcas SET Estado = 'anulada', Motivo = ?, FechaCierre = SYSDATETIME(), Usuario = ? "
                         "WHERE IdMarca = ? AND Estado = 'abierta'", (motivo, usuario, id_marca))


def cerrar_marca(id_marca: int, id_deuda: int) -> None:
    execute_write("UPDATE dbo.FacturasFaltantesMarcas SET Estado = 'cerrada', IdDeudaCierre = ?, FechaCierre = SYSDATETIME() "
                  "WHERE IdMarca = ? AND Estado = 'abierta'", (id_deuda, id_marca))


def guardar_perfil(id_contacto: int, campos: dict, usuario: str) -> None:
    sets = ", ".join(f"{k} = ?" for k in campos)
    execute_write_transaction([
        ("INSERT INTO dbo.FacturasFaltantesPerfil (IdContacto, Usuario) SELECT ?, ? "
         "WHERE NOT EXISTS (SELECT 1 FROM dbo.FacturasFaltantesPerfil WHERE IdContacto = ?)", (id_contacto, usuario, id_contacto)),
        (f"UPDATE dbo.FacturasFaltantesPerfil SET {sets}, Usuario = ?, FechaModificacion = SYSDATETIME() WHERE IdContacto = ?",
         (*campos.values(), usuario, id_contacto)),
    ])
