"""Carga de solo lectura para la auditoría de cuentas — 035 (T005)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from src.db.connection import fetch_all
from src.features.auditoria_cuentas.clasificacion import _dia
from src.features.auditoria_cuentas import conocidos
from src.features.auditoria_cuentas.hallazgos import ORGANISMOS
from src.features.recalculo_fifo.entrada import EXCLUIDOS


def fecha_corte() -> date:
    f = fetch_all("SELECT MAX(FechaCorte) AS c FROM dbo.SaldosReferenciaAccess", ())[0]["c"]
    return _dia(f)


def cargar(corte: date | None = None) -> dict:
    corte = corte or fecha_corte()
    tope = datetime.combine(corte, datetime.max.time().replace(microsecond=0))
    wc = fetch_all("SELECT Origen, IdOrigen, IdContacto, Fecha, Deuda, Credito FROM dbo.vw_MovimientosCuenta_Base "
                   "WHERE IdContacto IS NOT NULL AND Fecha <= ?", (tope,))
    ref = fetch_all("SELECT Origen, IdOrigen, IdContacto, Fecha, Deuda, Credito FROM dbo.SaldosReferenciaAccessDetalle", ())
    filas_wc: dict[int, list] = defaultdict(list)
    saldo_wc: dict[int, float] = defaultdict(float)
    for f in wc:
        filas_wc[f["IdContacto"]].append(f)
        saldo_wc[f["IdContacto"]] += float(f["Credito"] or 0) - float(f["Deuda"] or 0)
    filas_ref: dict[int, list] = defaultdict(list)
    max_fecha_ref: dict[str, date] = {}
    claves_ref: set[tuple] = set()
    for f in ref:
        filas_ref[f["IdContacto"]].append(f)
        claves_ref.add((f["Origen"], int(f["IdOrigen"])))
        d = _dia(f["Fecha"])
        if d and d > max_fecha_ref.get(f["Origen"], date.min):
            max_fecha_ref[f["Origen"]] = d
    saldo_ref = {r["IdContacto"]: float(r["SaldoAccess"]) for r in
                 fetch_all("SELECT IdContacto, SaldoAccess FROM dbo.SaldosReferenciaAccess", ())}
    reasignados = {(r["Origen"], int(r["IdOrigen"])) for r in fetch_all("SELECT Origen, IdOrigen FROM dbo.ReasignacionesContacto", ())}
    razon = {r["IdContacto"]: r["rs"] for r in fetch_all("SELECT IdContacto, [Razon Social] AS rs FROM dbo.Contactos", ())}
    moneda = {r["c"]: "Dolares" for r in fetch_all(
        "SELECT IdContacto AS c FROM dbo.Compras GROUP BY IdContacto "
        "HAVING SUM(CASE WHEN Moneda = 'Dolares' THEN 1 ELSE 0 END) * 2 > COUNT(*)", ())}
    return {"corte": corte, "saldoWc": dict(saldo_wc), "saldoRef": saldo_ref, "filasWc": filas_wc, "filasRef": filas_ref,
            "origenesRef": {f["Origen"] for f in ref}, "maxFechaRef": max_fecha_ref, "clavesRef": claves_ref,
            "reasignados": reasignados, "razon": razon, "moneda": moneda, "excluidos": set(EXCLUIDOS) - set(ORGANISMOS),
            "documentadas": {int(k["clave"]): {"importeRef": float(k["importeRef"] or 0), "motivo": k["motivo"]}
                             for k in conocidos.listar() if k["tipo"] == "cuenta"}}


def cargar_hallazgos(corte: date | None = None) -> dict:
    """Aplicaciones, documentos, notas y contactos para los hallazgos de la auditoría (solo lectura)."""
    fechas: dict[tuple, date | None] = {}
    for f in fetch_all("SELECT IdMovimientoBNA AS i, [Fecha / Hora Mov#] AS f FROM dbo.[Movimientos BNA]", ()):
        fechas[("bna", f["i"])] = _dia(f["f"])
    for f in fetch_all("SELECT IdMovimiento AS i, Fecha AS f FROM dbo.[Movimientos Galicia]", ()):
        fechas[("galicia", f["i"])] = _dia(f["f"])
    for f in fetch_all("SELECT IdPagoEfectivo AS i, Fecha AS f FROM dbo.[Pagos efectivo]", ()):
        fechas[("efectivo", f["i"])] = _dia(f["f"])
    filas = fetch_all(
        "SELECT a.IdAplicacion, a.OrigenMovimiento AS medio, a.IdMovimientoOrigen AS idMov, a.IdDocumentoAplicado AS idCompra, "
        "a.ImporteAplicado AS importe, a.Origen AS origen, c.IdContacto AS idContacto, c.[Nro Documento] AS nro, "
        "c.Fecha AS fechaFactura, v.ImporteDocumento AS total, v.Moneda AS moneda, v.[Tipo de Cambio] AS tc "
        "FROM dbo.AplicacionesPago a JOIN dbo.Compras c ON c.IdDeuda = a.IdDocumentoAplicado "
        "JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda "
        "WHERE a.Anulada = 0 AND a.TipoDocumento = 'CompraDeuda'", ())
    tarjeta = {f["i"]: float(f["s"]) for f in fetch_all(
        "SELECT IdCompra AS i, SUM(ImporteImputado) AS s FROM dbo.Tarjetas_Resumenes_Lineas_Compras GROUP BY IdCompra", ())}
    aplicaciones, docs = [], {}
    for f in filas:
        aplicaciones.append({
            "idAplicacion": f["IdAplicacion"], "medio": f["medio"], "idMovimiento": f["idMov"],
            "fechaPago": fechas.get((f["medio"], f["idMov"])), "idContacto": f["idContacto"], "idCompra": f["idCompra"],
            "fechaFactura": _dia(f["fechaFactura"]), "importe": float(f["importe"]), "origenAplicacion": f["origen"]})
        total = float(f["total"] or 0)
        if f["moneda"] == "Dolares" and f["tc"]:
            total *= float(f["tc"])
        d = docs.setdefault(f["idCompra"], {"idCompra": f["idCompra"], "idContacto": f["idContacto"], "nro": f["nro"], "total": total,
                                            "tarjeta": tarjeta.get(f["idCompra"], 0.0), "aplicado": 0.0, "bancarias": []})
        d["aplicado"] += float(f["importe"])
        if f["medio"] in ("bna", "galicia", "efectivo"):
            d["bancarias"].append({"idAplicacion": f["IdAplicacion"], "medio": f["medio"], "idMovimiento": f["idMov"], "importe": float(f["importe"]),
                                   "fechaPago": fechas.get((f["medio"], f["idMov"])), "origenAplicacion": f["origen"]})
    notas = [{"idContacto": f["IdContacto"], "nro": f["nro"], "total": float(f["total"]), "aplicado": float(f["ap"] or 0),
              "tarjeta": float(f["tj"] or 0)} for f in fetch_all(
        "SELECT c.IdContacto, c.[Nro Documento] AS nro, v.ImporteDocumento AS total, "
        "(SELECT SUM(a.ImporteAplicado) FROM dbo.AplicacionesPago a WHERE a.Anulada = 0 AND a.IdDocumentoAplicado = c.IdDeuda) AS ap, "
        "(SELECT SUM(t.ImporteImputado) FROM dbo.Tarjetas_Resumenes_Lineas_Compras t WHERE t.IdCompra = c.IdDeuda) AS tj "
        "FROM dbo.Compras c JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda "
        "WHERE c.[Tipo documento] LIKE 'Nota de D%' AND c.Fecha <= ?", (datetime.combine(corte or fecha_corte(), datetime.min.time()),))]
    contactos = [{"idContacto": f["i"], "razonSocial": f["rs"], "cuit": f["c"]} for f in fetch_all(
        "SELECT IdContacto AS i, [Razon Social] AS rs, [CUIT/CUIL] AS c FROM dbo.Contactos", ())]
    corte = corte or fecha_corte()
    tope = datetime.combine(corte, datetime.max.time().replace(microsecond=0))
    reasig = {(r["Origen"], int(r["IdOrigen"])) for r in fetch_all("SELECT Origen, IdOrigen FROM dbo.ReasignacionesContacto", ())}
    sin_contacto = [
        {"medio": "bna", "idMovimiento": f["i"], "fecha": _dia(f["f"]), "importe": float(f["m"]), "concepto": f["c"]}
        for f in fetch_all(
            "SELECT IdMovimientoBNA AS i, [Fecha / Hora Mov#] AS f, Importe AS m, Concepto AS c FROM dbo.[Movimientos BNA] b "
            "WHERE ISNULL(IdContacto, 0) = 0 AND [Fecha / Hora Mov#] <= ? "
            "AND NOT EXISTS (SELECT 1 FROM dbo.ConciliacionesTesoreria t WHERE t.Medio = 'bna' AND t.IdMovimiento = b.IdMovimientoBNA) "
            "AND NOT EXISTS (SELECT 1 FROM dbo.TarjetasCruces x WHERE x.Deshecho = 0 AND x.MedioOrigen = 'bna' AND x.IdMovimientoOrigen = b.IdMovimientoBNA)", (tope,))
        if ("Banco Nacion", f["i"]) not in reasig]
    sin_contacto += [
        {"medio": "galicia", "idMovimiento": f["i"], "fecha": _dia(f["f"]), "importe": float(f["m"] or 0), "concepto": f["c"]}
        for f in fetch_all(
            "SELECT IdMovimiento AS i, Fecha AS f, ISNULL([Créditos], 0) - ISNULL([Débitos], 0) AS m, [Descripción] AS c "
            "FROM dbo.[Movimientos Galicia] g WHERE ISNULL(IdContacto, 0) = 0 AND Fecha <= ? "
            "AND NOT EXISTS (SELECT 1 FROM dbo.ConciliacionesTesoreria t WHERE t.Medio = 'galicia' AND t.IdMovimiento = g.IdMovimiento) "
            "AND NOT EXISTS (SELECT 1 FROM dbo.TarjetasCruces x WHERE x.Deshecho = 0 AND x.MedioOrigen = 'galicia' AND x.IdMovimientoOrigen = g.IdMovimiento)", (tope,))
        if ("Galicia", f["i"]) not in reasig]
    saldos_org = {r["c"]: float(r["s"]) for r in fetch_all(
        "SELECT IdContacto AS c, SUM(Credito - Deuda) AS s FROM dbo.vw_MovimientosCuenta_Base WHERE Fecha <= ? "
        f"AND IdContacto IN ({','.join(str(i) for i in ORGANISMOS)}) GROUP BY IdContacto", (tope,))}
    try:
        compartidos = [r["k"] for r in fetch_all("SELECT Clave AS k FROM dbo.AuditoriaConocidos WHERE Activo = 1 AND Tipo = 'cuit-compartido'", ())]
    except Exception:
        compartidos = []  # sin tabla o sin el tipo todavía
    return {"aplicaciones": aplicaciones, "documentos": list(docs.values()), "notas": notas, "contactos": contactos,
            "saldosOrganismos": saldos_org, "movimientosSinContacto": sin_contacto, "cuitsCompartidos": compartidos}
