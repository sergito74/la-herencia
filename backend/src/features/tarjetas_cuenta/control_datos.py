"""Carga de solo lectura para el control de integridad de las tarjetas — 034 (T034)."""

from __future__ import annotations

from datetime import date, datetime

from src.db.connection import fetch_all, fetch_one
from src.features.tarjetas import repository as tarjetas_repository
from src.features.tarjetas.compensaciones import get_compensaciones
from src.features.tarjetas_cuenta import control as ctl
from src.features.tarjetas_cuenta import repository as cuenta


def _dia(valor):
    return valor.date() if isinstance(valor, datetime) else valor


def cargar_control() -> dict:
    tarjetas = tarjetas_repository.get_tarjetas(False)
    contactos = {t["idTarjeta"]: tarjetas_repository.get_id_contacto_tarjeta(t["idTarjeta"]) for t in tarjetas}
    anteriores = {i: a["idContactoAnterior"] for i, a in cuenta._contactos_anteriores().items() if a["idContactoAnterior"]}
    contacto_a_tarjeta = {c: i for i, c in contactos.items() if c is not None}
    contacto_a_tarjeta.update({c: i for i, c in anteriores.items()})
    ids = list(contacto_a_tarjeta)
    marcas = ",".join("?" * len(ids)) if ids else "NULL"

    bna = fetch_all(
        "SELECT 'bna' AS medio, IdMovimientoBNA AS id, [Fecha / Hora Mov#] AS fecha, Importe AS importe, IdContacto AS c "
        f"FROM dbo.[Movimientos BNA] WHERE IdContacto IN ({marcas})", tuple(ids))
    gal = fetch_all(
        "SELECT 'galicia' AS medio, IdMovimiento AS id, Fecha AS fecha, ISNULL([Créditos],0)-ISNULL([Débitos],0) AS importe, "
        f"IdContacto AS c FROM dbo.[Movimientos Galicia] WHERE IdContacto IN ({marcas})", tuple(ids))

    mov_pago = {}
    for f in fetch_all("SELECT IdMovimientoBNA AS id, Importe AS imp, IdContacto AS c FROM dbo.[Movimientos BNA]"):
        mov_pago[("BNA", f["id"])] = (f["imp"], f["c"])
    for f in fetch_all("SELECT IdMovimiento AS id, ISNULL([Créditos],0)-ISNULL([Débitos],0) AS imp, IdContacto AS c "
                       "FROM dbo.[Movimientos Galicia]"):
        mov_pago[("Galicia", f["id"])] = (f["imp"], f["c"])

    pagos, con_resumen = [], set()
    for p in fetch_all(
        "SELECT p.IdPago, p.IdResumen, p.Fecha, p.Importe, p.Origen, p.IdMovimientoOrigen, r.IdTarjeta, r.EstadoResumen "
        "FROM dbo.Tarjetas_Resumenes_Pagos p JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = p.IdResumen"):
        clave = (p["Origen"], p["IdMovimientoOrigen"]) if p["IdMovimientoOrigen"] is not None else None
        imp, contacto = mov_pago.get(clave, (None, None)) if clave else (None, None)
        medio = {"BNA": "bna", "Galicia": "galicia"}.get(p["Origen"])
        if clave and medio:
            con_resumen.add((medio, p["IdMovimientoOrigen"]))
        pagos.append({"idPago": p["IdPago"], "idResumen": p["IdResumen"], "idTarjeta": p["IdTarjeta"], "fecha": _dia(p["Fecha"]),
                      "importe": float(p["Importe"] or 0), "medio": medio, "idMovimientoOrigen": p["IdMovimientoOrigen"],
                      "importeMovimiento": float(imp) if imp is not None else None, "contactoMovimiento": contacto,
                      "estadoResumen": p["EstadoResumen"], "origen": p["Origen"]})

    cruces: set = set()
    if fetch_one("SELECT OBJECT_ID('dbo.TarjetasCruces', 'U') AS t", ())["t"] is not None:
        for f in fetch_all("SELECT MedioOrigen AS m, IdMovimientoOrigen AS i FROM dbo.TarjetasCruces "
                           "WHERE Deshecho = 0 AND Tipo = 'devolucion-debito'"):
            cruces.add((f["m"], f["i"]))
        for f in fetch_all("SELECT MedioDestino AS m, IdMovimientoDestino AS i FROM dbo.TarjetasCruces "
                           "WHERE Deshecho = 0 AND Tipo = 'devolucion-debito'"):
            cruces.add((f["m"], f["i"]))

    reasignados = {({"Banco Nacion": "bna", "Galicia": "galicia"}.get(f["o"], ""), f["i"])
                   for f in fetch_all("SELECT Origen AS o, IdOrigen AS i FROM dbo.ReasignacionesContacto")}
    movimientos_tarjeta, debitos = [], []
    for f in bna + gal:
        if f["importe"] is None:
            continue
        t = contacto_a_tarjeta[f["c"]]
        if f["importe"] < 0:
            debitos.append({"idTarjeta": t, "fecha": _dia(f["fecha"]), "importe": abs(float(f["importe"]))})
        if f["c"] in anteriores.values() or (f["medio"], f["id"]) in reasignados:
            continue  # administración anterior: apertura informativa, no faltante
        movimientos_tarjeta.append({
            "idTarjeta": t, "medio": f["medio"], "idMovimiento": f["id"], "fecha": _dia(f["fecha"]),
            "importe": float(f["importe"]), "tieneResumen": (f["medio"], f["id"]) in con_resumen,
            "esCruzado": (f["medio"], f["id"]) in cruces})

    creditos = [{"medio": "bna", "idMovimiento": f["id"], "fecha": _dia(f["fecha"]), "importe": float(f["importe"])}
                for f in fetch_all("SELECT IdMovimientoBNA AS id, [Fecha / Hora Mov#] AS fecha, Importe AS importe "
                                   "FROM dbo.[Movimientos BNA] WHERE Importe > 0 AND ISNULL(IdContacto, 0) = 0")]
    creditos += [{"medio": "galicia", "idMovimiento": f["id"], "fecha": _dia(f["fecha"]), "importe": float(f["importe"])}
                 for f in fetch_all("SELECT IdMovimiento AS id, Fecha AS fecha, [Créditos] AS importe "
                                    "FROM dbo.[Movimientos Galicia] WHERE [Créditos] > 0 AND ISNULL(IdContacto, 0) = 0")]

    resumenes, consumos = [], []
    for t in tarjetas:
        comp = get_compensaciones(t["idTarjeta"])
        for r in fetch_all("SELECT IdResumen AS id, FechaCierre AS cierre, EstadoResumen AS estado "
                           "FROM dbo.Tarjetas_Resumenes WHERE IdTarjeta = ?", (t["idTarjeta"],)):
            resumenes.append({"idResumen": r["id"], "idTarjeta": t["idTarjeta"], "fechaCierre": _dia(r["cierre"]),
                              "estado": r["estado"], "pendiente": float(comp.get(r["id"], {}).get("saldoPendiente", 0) or 0)})
        extra = {f["id"]: f for f in fetch_all(
            "SELECT l.IdLineaConsumo AS id, l.FechaCompra AS fecha, l.Observaciones AS obs FROM dbo.Tarjetas_Resumenes_Lineas l "
            "JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = l.IdResumen WHERE r.IdTarjeta = ?", (t["idTarjeta"],))}
        for id_l, c in cuenta._cargar_consumos(t["idTarjeta"]).items():
            consumos.append({"idTarjeta": t["idTarjeta"], "idLineaConsumo": id_l, "idResumen": c["idResumen"],
                             "fecha": _dia(extra[id_l]["fecha"]), "detalle": c["detalle"], "observaciones": extra[id_l]["obs"],
                             "importe": c["importe"], "vinculado": c["vinculado"], "tieneProveedor": c["tieneProveedor"],
                             "cruzado": c["cruzado"], "proveedorDebe": c["tieneProveedor"] and c["importe"] - c["vinculado"] > 0})

    saldos = [{"idTarjeta": s["idTarjeta"], "saldo": s["saldo"], "pendienteNeto": s["pendienteNeto"]}
              for s in cuenta.resumen_tarjetas()["tarjetas"]]
    return {"hoy": date.today(), "tarjetas": [{**t, "idContacto": contactos[t["idTarjeta"]]} for t in tarjetas],
            "contactosTarjeta": set(contacto_a_tarjeta), "pagos": pagos, "movimientosTarjeta": movimientos_tarjeta,
            "debitosTarjeta": debitos, "creditosSinContacto": creditos, "crucesVigentes": cruces,
            "resumenes": resumenes, "consumos": consumos, "saldos": saldos}


def control(id_tarjeta: int | None = None, categoria: str | None = None) -> dict:
    items = ctl.hallazgos(cargar_control())
    if id_tarjeta is not None:
        items = [h for h in items if h["idTarjeta"] == id_tarjeta]
    resumen = ctl.resumen_por_categoria(items)
    if categoria:
        items = [h for h in items if h["categoria"] == categoria]
    return {"generado": datetime.now(), "resumenPorCategoria": resumen, "hallazgos": items}
