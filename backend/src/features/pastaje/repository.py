"""039: SQL de pastaje. Escrituras en una transacción con concurrencia optimista (Version)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.db.connection import execute_write_transaction, fetch_all, fetch_one


class Conflicto(Exception):
    """El registro cambió desde que se leyó, o la operación no es válida en su estado (409)."""


class NoExiste(Exception):
    pass


def _d(x) -> Decimal:
    return Decimal(str(x)) if x is not None else Decimal(0)


def _iso(x):
    return x.isoformat() if isinstance(x, date) else x


def _transaccion(stmts: list, *, version_rows: tuple[int, ...] = ()) -> list:
    """Ejecuta y verifica que los UPDATE con Version afectaron exactamente una fila."""
    res = execute_write_transaction(stmts)
    if any(res[i] != 1 for i in version_rows):
        raise Conflicto("El registro fue modificado por otra persona. Volvé a cargarlo.")
    return res


# --- Catálogos ---------------------------------------------------------------

def categorias() -> dict[int, str]:
    return {r["i"]: r["n"] for r in fetch_all("SELECT IdTipoHacienda i, [Tipo de Hacienda] n FROM dbo.[Tipo Hacienda]")}


def contacto(id_contacto: int) -> dict | None:
    return fetch_one("SELECT IdContacto id, [Razon Social] razonSocial, [CUIT/CUIL] cuit FROM dbo.Contactos WHERE IdContacto=?",
                     (id_contacto,))


def id_campania(nombre: str) -> int | None:
    r = fetch_one("SELECT IdCampaña i FROM dbo.Campañas WHERE Campaña=?", (nombre,))
    return r["i"] if r else None


# --- Contratos ---------------------------------------------------------------

_CONTRATO = (
    "SELECT c.IdContratoPastaje id, c.IdContactoCliente idContacto, ct.[Razon Social] cliente, ct.[CUIT/CUIL] cuit, "
    "c.IdEstablecimiento idEstablecimiento, e.Establecimiento establecimiento, "
    "CONVERT(varchar(10), c.FechaInicio, 23) fechaInicio, CONVERT(varchar(10), c.FechaFin, 23) fechaFin, "
    "c.Modalidad modalidad, c.CondicionVenta condicionVenta, CAST(c.AlicuotaIva AS varchar(10)) alicuotaIva, "
    "c.CarpetaDocumentos carpetaDocumentos, c.ArchivoContrato archivoContrato, "
    "c.ClausulaInfraestructura clausulaInfraestructura, c.ClausulaSanidad clausulaSanidad, "
    "c.ClausulaMortandad clausulaMortandad, c.OtrasClausulas otrasClausulas, c.Estado estado, "
    "c.MotivoEstado motivoEstado, c.Version version "
    "FROM dbo.ContratosPastaje c JOIN dbo.Contactos ct ON ct.IdContacto=c.IdContactoCliente "
    "LEFT JOIN dbo.Establecimientos e ON e.Id=c.IdEstablecimiento"
)


def contratos(estado: str | None = None) -> list[dict]:
    if estado:
        return fetch_all(_CONTRATO + " WHERE c.Estado=? ORDER BY c.FechaInicio DESC", (estado,))
    return fetch_all(_CONTRATO + " ORDER BY CASE c.Estado WHEN 'vigente' THEN 0 ELSE 1 END, c.FechaInicio DESC")


def contrato(id_contrato: int) -> dict:
    r = fetch_one(_CONTRATO + " WHERE c.IdContratoPastaje=?", (id_contrato,))
    if not r:
        raise NoExiste(f"No existe el contrato {id_contrato}.")
    return r


def tarifas(id_contrato: int) -> list[dict]:
    return fetch_all(
        "SELECT IdTarifa id, IdTipoHacienda idTipoHacienda, TipoTarifa tipoTarifa, CAST(Valor AS varchar(30)) valor, "
        "CONVERT(varchar(10), VigenteDesde, 23) vigenteDesde FROM dbo.PastajeTarifas WHERE IdContratoPastaje=? "
        "ORDER BY IdTipoHacienda, VigenteDesde", (id_contrato,))


_CAMPOS = ("IdContactoCliente", "FechaInicio", "FechaFin", "CarpetaDocumentos", "ArchivoContrato",
           "ClausulaInfraestructura", "ClausulaSanidad", "ClausulaMortandad", "OtrasClausulas")


def _valores(d: dict) -> tuple:
    return tuple(_iso(d.get(k)) for k in ("idContacto", "fechaInicio", "fechaFin", "carpetaDocumentos", "archivoContrato",
                                          "clausulaInfraestructura", "clausulaSanidad", "clausulaMortandad", "otrasClausulas"))


def _insert_tarifa(t: dict, usuario: str, id_contrato=None):
    sql = ("INSERT INTO dbo.PastajeTarifas (IdContratoPastaje, IdTipoHacienda, TipoTarifa, Valor, VigenteDesde, CreadoPor) "
           "VALUES (?,?,?,?,?,?)")
    vals = (t["idTipoHacienda"], t["tipoTarifa"], str(t["valor"]), _iso(t["vigenteDesde"]), usuario)
    if id_contrato is not None:
        return (sql, (id_contrato,) + vals)
    return lambda res: (sql, (res[0],) + vals)


def insertar_contrato(d: dict, tarifas_: list[dict], usuario: str, empresa: int, establecimiento: int) -> int:
    stmts = [(f"INSERT INTO dbo.ContratosPastaje ({', '.join(_CAMPOS)}, IdEmpresaContacto, IdEstablecimiento, CreadoPor) "
              f"OUTPUT INSERTED.IdContratoPastaje VALUES ({', '.join('?' * (len(_CAMPOS) + 3))})",
              _valores(d) + (empresa, establecimiento, usuario))]
    stmts += [_insert_tarifa(t, usuario) for t in tarifas_]
    return _transaccion(stmts)[0]


def actualizar_contrato(id_contrato: int, d: dict, tarifas_nuevas: list[dict], version: int, usuario: str) -> None:
    sets = ", ".join(f"{c}=?" for c in _CAMPOS)
    stmts = [(f"UPDATE dbo.ContratosPastaje SET {sets}, ModificadoPor=?, ModificadoEn=SYSDATETIME(), Version=Version+1 "
              "WHERE IdContratoPastaje=? AND Version=? AND Estado='vigente'",
              _valores(d) + (usuario, id_contrato, version))]
    stmts += [_insert_tarifa(t, usuario, id_contrato) for t in tarifas_nuevas]
    _transaccion(stmts, version_rows=(0,))


def cambiar_estado(id_contrato: int, estado: str, motivo: str, fecha_fin: date | None, version: int, usuario: str) -> None:
    _transaccion([(
        "UPDATE dbo.ContratosPastaje SET Estado=?, MotivoEstado=?, FechaFin=COALESCE(?, FechaFin), ModificadoPor=?, "
        "ModificadoEn=SYSDATETIME(), Version=Version+1 WHERE IdContratoPastaje=? AND Version=? AND Estado='vigente'",
        (estado, motivo, _iso(fecha_fin), usuario, id_contrato, version))], version_rows=(0,))


# --- Bitácora ----------------------------------------------------------------

def bitacora(id_contrato: int) -> list[dict]:
    return fetch_all(
        "SELECT b.IdMovimiento id, CONVERT(varchar(10), b.Fecha, 23) fecha, b.Tipo tipo, b.IdTipoHacienda idTipoHacienda, "
        "th.[Tipo de Hacienda] categoria, b.Cabezas cabezas, b.CabezasSistema cabezasSistema, b.NumeroDTe numeroDte, "
        "b.Observacion observacion, b.Estado estado, b.MotivoAnulacion motivoAnulacion, b.CreadoPor creadoPor, "
        "b.Version version FROM dbo.PastajeBitacora b LEFT JOIN dbo.[Tipo Hacienda] th ON th.IdTipoHacienda=b.IdTipoHacienda "
        "WHERE b.IdContratoPastaje=? ORDER BY b.Fecha, b.IdMovimiento", (id_contrato,))


def insertar_movimiento(id_contrato: int, m: dict, cabezas_sistema: int | None, usuario: str) -> int:
    return _transaccion([(
        "INSERT INTO dbo.PastajeBitacora (IdContratoPastaje, Fecha, Tipo, IdTipoHacienda, Cabezas, CabezasSistema, NumeroDTe, "
        "Observacion, CreadoPor) OUTPUT INSERTED.IdMovimiento VALUES (?,?,?,?,?,?,?,?,?)",
        (id_contrato, _iso(m["fecha"]), m["tipo"], m["idTipoHacienda"], m["cabezas"], cabezas_sistema,
         m.get("numeroDte"), m.get("observacion"), usuario))])[0]


def movimiento(id_mov: int) -> dict:
    r = fetch_one("SELECT IdMovimiento id, IdContratoPastaje idContrato, CONVERT(varchar(10), Fecha, 23) fecha, Estado estado, "
                  "Version version FROM dbo.PastajeBitacora WHERE IdMovimiento=?", (id_mov,))
    if not r:
        raise NoExiste(f"No existe el movimiento {id_mov}.")
    return r


def anular_movimiento(id_mov: int, motivo: str, version: int, usuario: str) -> None:
    _transaccion([(
        "UPDATE dbo.PastajeBitacora SET Estado='anulado', MotivoAnulacion=?, ModificadoPor=?, ModificadoEn=SYSDATETIME(), "
        "Version=Version+1 WHERE IdMovimiento=? AND Version=? AND Estado='vigente'",
        (motivo, usuario, id_mov, version))], version_rows=(0,))


# --- Liquidaciones -----------------------------------------------------------

_LIQ = ("SELECT l.IdLiquidacion id, l.IdContratoPastaje idContrato, CONVERT(varchar(10), l.Periodo, 23) periodo, l.Tipo tipo, "
        "l.IdLiquidacionOriginal idLiquidacionOriginal, l.Estado estado, CAST(l.PrecioPromedio AS varchar(30)) precioPromedio, "
        "CAST(l.KgTotal AS varchar(30)) kg, CAST(l.Neto AS varchar(30)) neto, CAST(l.Iva AS varchar(30)) iva, "
        "CAST(l.Total AS varchar(30)) total, l.Moneda moneda, l.ArchivoPdf archivoPdf, l.ConfirmadaPor confirmadaPor, "
        "l.ConfirmadaEn confirmadaEn, l.Version version FROM dbo.PastajeLiquidaciones l")


def liquidaciones(id_contrato: int) -> list[dict]:
    return fetch_all(_LIQ + " WHERE l.IdContratoPastaje=? ORDER BY l.Periodo DESC, l.IdLiquidacion DESC", (id_contrato,))


def liquidacion(id_liq: int) -> dict:
    r = fetch_one(_LIQ + " WHERE l.IdLiquidacion=?", (id_liq,))
    if not r:
        raise NoExiste(f"No existe la liquidación {id_liq}.")
    r["tramos"] = fetch_all(
        "SELECT t.IdTipoHacienda idTipoHacienda, th.[Tipo de Hacienda] categoria, CONVERT(varchar(10), t.Desde, 23) desde, "
        "CONVERT(varchar(10), t.Hasta, 23) hasta, t.Cabezas cabezas, t.Dias dias, t.TipoTarifa tipoTarifa, "
        "CAST(t.ValorMes AS varchar(30)) valorMes, CAST(t.Kg AS varchar(30)) kg, CAST(t.Importe AS varchar(30)) importe "
        "FROM dbo.PastajeLiquidacionTramos t LEFT JOIN dbo.[Tipo Hacienda] th ON th.IdTipoHacienda=t.IdTipoHacienda "
        "WHERE t.IdLiquidacion=? ORDER BY t.IdTramo", (id_liq,))
    r["indices"] = fetch_all("SELECT CONVERT(varchar(10), Fecha, 23) fecha, CAST(Indice AS varchar(30)) indice "
                             "FROM dbo.PastajeLiquidacionIndices WHERE IdLiquidacion=? ORDER BY Fecha", (id_liq,))
    return r


def mensual_vigente(id_contrato: int, periodo: date) -> dict | None:
    r = fetch_one("SELECT IdLiquidacion id FROM dbo.PastajeLiquidaciones WHERE IdContratoPastaje=? AND Periodo=? "
                  "AND Tipo='mensual' AND Estado<>'anulada'", (id_contrato, periodo.isoformat()))
    return liquidacion(r["id"]) if r else None


def _detalle(liq, id_ref) -> list:
    out = []
    for t in liq.tramos:
        out.append(lambda res, t=t: (
            "INSERT INTO dbo.PastajeLiquidacionTramos (IdLiquidacion, IdTipoHacienda, Desde, Hasta, Cabezas, Dias, TipoTarifa, "
            "ValorMes, Kg, Importe) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (id_ref(res), t.categoria, t.desde.isoformat(), t.hasta.isoformat(), t.cabezas, t.dias, t.tipo,
             str(t.valor_mes), str(round(t.kg, 4)), str(round(t.importe, 4)))))
    for f, v in liq.indices:
        out.append(lambda res, f=f, v=v: (
            "INSERT INTO dbo.PastajeLiquidacionIndices (IdLiquidacion, Fecha, Indice) VALUES (?,?,?)",
            (id_ref(res), f.isoformat(), str(v))))
    return out


def guardar_borrador(id_contrato: int, liq, usuario: str, tipo: str = "mensual", original: int | None = None,
                     existente: dict | None = None, importes: tuple | None = None) -> int:
    """Crea o reemplaza (si es borrador) la liquidación. `importes` permite fijar neto/iva/total (ajuste)."""
    neto, iva, total = importes or (liq.neto, liq.iva, liq.total)
    valores = (str(liq.precio) if liq.precio is not None else None, str(round(liq.kg, 4)), str(neto), str(iva), str(total), liq.moneda)
    if existente:
        if existente["estado"] != "borrador":
            raise Conflicto("La liquidación ya está confirmada: los cambios se resuelven con un ajuste.")
        lid = existente["id"]
        stmts = [("DELETE FROM dbo.PastajeLiquidacionTramos WHERE IdLiquidacion=?", (lid,)),
                 ("DELETE FROM dbo.PastajeLiquidacionIndices WHERE IdLiquidacion=?", (lid,)),
                 ("UPDATE dbo.PastajeLiquidaciones SET PrecioPromedio=?, KgTotal=?, Neto=?, Iva=?, Total=?, Moneda=?, "
                  "ModificadoPor=?, ModificadoEn=SYSDATETIME(), Version=Version+1 WHERE IdLiquidacion=? AND Version=? "
                  "AND Estado='borrador'", valores + (usuario, lid, existente["version"]))]
        _transaccion(stmts + _detalle(liq, lambda res: lid), version_rows=(2,))
        return lid
    stmts = [("INSERT INTO dbo.PastajeLiquidaciones (IdContratoPastaje, Periodo, Tipo, IdLiquidacionOriginal, PrecioPromedio, "
              "KgTotal, Neto, Iva, Total, Moneda, CreadoPor) OUTPUT INSERTED.IdLiquidacion VALUES (?,?,?,?,?,?,?,?,?,?,?)",
              (id_contrato, liq.periodo.isoformat(), tipo, original) + valores + (usuario,))]
    return _transaccion(stmts + _detalle(liq, lambda res: res[0]))[0]


def confirmar_liquidacion(id_liq: int, version: int, usuario: str) -> None:
    _transaccion([(
        "UPDATE dbo.PastajeLiquidaciones SET Estado='confirmada', ConfirmadaPor=?, ConfirmadaEn=SYSDATETIME(), "
        "Version=Version+1 WHERE IdLiquidacion=? AND Version=? AND Estado='borrador'",
        (usuario, id_liq, version))], version_rows=(0,))


def guardar_pdf_liquidacion(id_liq: int, ruta: str) -> None:
    execute_write_transaction([("UPDATE dbo.PastajeLiquidaciones SET ArchivoPdf=? WHERE IdLiquidacion=?", (ruta, id_liq))])


def anular_liquidacion(id_liq: int, version: int, usuario: str) -> None:
    _transaccion([(
        "UPDATE dbo.PastajeLiquidaciones SET Estado='anulada', ModificadoPor=?, ModificadoEn=SYSDATETIME(), Version=Version+1 "
        "WHERE IdLiquidacion=? AND Version=? AND Estado<>'anulada' AND NOT EXISTS (SELECT 1 FROM dbo.PastajeComprobantes c "
        "WHERE c.IdLiquidacion=? AND c.Estado='vigente')", (usuario, id_liq, version, id_liq))], version_rows=(0,))


# --- Comprobantes ------------------------------------------------------------

_COMP = ("SELECT c.IdComprobante id, c.IdContratoPastaje idContrato, c.IdLiquidacion idLiquidacion, c.Tipo tipo, c.Letra letra, "
         "c.PuntoVenta puntoVenta, c.Numero numero, CONVERT(varchar(10), c.Fecha, 23) fecha, "
         "CONVERT(varchar(10), c.VtoPago, 23) vtoPago, c.Cae cae, CONVERT(varchar(10), c.VtoCae, 23) vtoCae, "
         "c.CuitCliente cuitCliente, CONVERT(varchar(10), c.PeriodoDesde, 23) periodoDesde, "
         "CONVERT(varchar(10), c.PeriodoHasta, 23) periodoHasta, c.Detalle detalle, CAST(c.Neto AS varchar(30)) neto, "
         "CAST(c.Iva AS varchar(30)) iva, CAST(c.Total AS varchar(30)) total, c.IdComprobanteAsociado idComprobanteAsociado, "
         "c.IdCampania idCampania, c.ArchivoPdf archivoPdf, c.Estado estado, c.MotivoAnulacion motivoAnulacion, "
         "c.Version version FROM dbo.PastajeComprobantes c")


def comprobantes(id_contrato: int) -> list[dict]:
    return fetch_all(_COMP + " WHERE c.IdContratoPastaje=? ORDER BY c.Fecha, c.IdComprobante", (id_contrato,))


def comprobante(id_comp: int) -> dict:
    r = fetch_one(_COMP + " WHERE c.IdComprobante=?", (id_comp,))
    if not r:
        raise NoExiste(f"No existe el comprobante {id_comp}.")
    return r


def existe_numero(tipo: str, letra: str, pv: int, numero: int) -> bool:
    return bool(fetch_one("SELECT 1 x FROM dbo.PastajeComprobantes WHERE Tipo=? AND Letra=? AND PuntoVenta=? AND Numero=?",
                          (tipo, letra, pv, numero)))


def insertar_comprobante(c: dict, usuario: str) -> int:
    campos = ("IdContratoPastaje", "IdLiquidacion", "Tipo", "Letra", "PuntoVenta", "Numero", "Fecha", "VtoPago", "Cae", "VtoCae",
              "CuitCliente", "PeriodoDesde", "PeriodoHasta", "Detalle", "Neto", "Iva", "Total", "IdComprobanteAsociado",
              "IdCampania", "IdEstablecimiento", "ArchivoPdf")
    claves = ("idContrato", "idLiquidacion", "tipo", "letra", "puntoVenta", "numero", "fecha", "vtoPago", "cae", "vtoCae",
              "cuitCliente", "periodoDesde", "periodoHasta", "detalle", "neto", "iva", "total", "idComprobanteAsociado",
              "idCampania", "idEstablecimiento", "archivoPdf")
    vals = tuple(str(c[k]) if isinstance(c.get(k), Decimal) else _iso(c.get(k)) for k in claves)
    return _transaccion([(f"INSERT INTO dbo.PastajeComprobantes ({', '.join(campos)}, CreadoPor) OUTPUT INSERTED.IdComprobante "
                          f"VALUES ({', '.join('?' * (len(campos) + 1))})", vals + (usuario,))])[0]


def anular_comprobante(id_comp: int, motivo: str, version: int, usuario: str) -> None:
    _transaccion([(
        "UPDATE dbo.PastajeComprobantes SET Estado='anulado', MotivoAnulacion=?, ModificadoPor=?, ModificadoEn=SYSDATETIME(), "
        "Version=Version+1 WHERE IdComprobante=? AND Version=? AND Estado='vigente' AND NOT EXISTS (SELECT 1 FROM "
        "dbo.AplicacionesPago a WHERE a.TipoDocumento='Pastaje' AND a.IdDocumentoAplicado=? AND ISNULL(a.Anulada,0)=0)",
        (motivo, usuario, id_comp, version, id_comp))], version_rows=(0,))


def documentos_cliente(id_contacto: int) -> list[dict]:
    """Facturas y ND vigentes del cliente con su total neto de NC asociadas (insumo de cobros)."""
    return fetch_all(
        "SELECT c.IdComprobante idDocumento, c.Fecha fecha, "
        "c.Letra + ' ' + RIGHT('0000' + CAST(c.PuntoVenta AS varchar(5)), 4) + '-' + RIGHT('00000000' + CAST(c.Numero AS varchar(8)), 8) "
        "numeroDocumento, c.Total - ISNULL((SELECT SUM(n.Total) FROM dbo.PastajeComprobantes n WHERE n.IdComprobanteAsociado="
        "c.IdComprobante AND n.Tipo='nota_credito' AND n.Estado='vigente'), 0) total "
        "FROM dbo.PastajeComprobantes c JOIN dbo.ContratosPastaje k ON k.IdContratoPastaje=c.IdContratoPastaje "
        "WHERE k.IdContactoCliente=? AND c.Estado='vigente' AND c.Tipo IN ('factura','nota_debito') ORDER BY c.Fecha", (id_contacto,))


def saldo_documento(id_comp: int) -> dict:
    r = fetch_one(
        "SELECT c.Total - ISNULL((SELECT SUM(n.Total) FROM dbo.PastajeComprobantes n WHERE n.IdComprobanteAsociado=c.IdComprobante "
        "AND n.Tipo='nota_credito' AND n.Estado='vigente'), 0) total FROM dbo.PastajeComprobantes c "
        "WHERE c.IdComprobante=? AND c.Estado='vigente' AND c.Tipo IN ('factura','nota_debito')", (id_comp,))
    return {"total": _d(r["total"]) if r else Decimal(0)}


def cobrado(ids: list[int]) -> dict[int, Decimal]:
    if not ids:
        return {}
    from src.features.vinculos import fuente

    pagado = fuente.pagado_de_documentos([("Pastaje", i) for i in ids])
    return {i: _d(pagado[("Pastaje", i)]) for i in ids}
