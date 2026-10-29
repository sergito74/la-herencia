"""044 — Tablero de facturas esperadas, alarmas "a verificar" y marcas de falta factura. Solo lectura de la contabilidad."""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import date, datetime, timedelta

from src.features.facturas_faltantes import repository as repo
from src.features.facturas_faltantes.motor import CICLOS, Comprobante, Perfil, agrupar, aprender_ciclo, evaluar

_CACHE: dict = {}
_TTL = 600
VENTANA_PAGO = 60
SALDO_A_FAVOR_DIAS = 90
RETENCION_DIAS = 30
REMITO_DIAS = 60
DESDE_PAGOS = date(2020, 1, 1)
MESES_HISTORICO = 24


def invalidar() -> None:
    _CACHE.clear()


def _dia(v) -> date:
    return v.date() if isinstance(v, datetime) else v


def _datos() -> dict:
    if _CACHE.get("t", 0) > time.time() - _TTL:
        return _CACHE["d"]
    provs = repo.proveedores()
    docs = defaultdict(list)
    for c in repo.comprobantes():
        if c["idContacto"] in provs:
            docs[c["idContacto"]].append({**c, "fecha": _dia(c["fecha"]), "importe": float(c["importe"] or 0)})
    pagos = defaultdict(list)
    for p in repo.pagos():
        if p["idContacto"] in provs:
            pagos[p["idContacto"]].append({**p, "fecha": _dia(p["fecha"]), "importe": float(p["importe"] or 0),
                                           "medio": repo.MEDIOS[p["origen"]]})
    deudas = defaultdict(list)
    for x in repo.fechas_de_deuda():
        if x["idContacto"] in provs and x["fecha"]:
            deudas[x["idContacto"]].append(_dia(x["fecha"]))
    d = {"deudas": deudas, "provs": provs, "docs": docs, "pagos": pagos, "aplicados": repo.pagos_aplicados(), "perfiles": repo.perfiles(),
         "saldos": {s["idContacto"]: s for s in repo.saldos()}, "retenciones": repo.retenciones(),
         "remitos": repo.remitos_sin_factura()}
    _CACHE.update(t=time.time(), d=d)
    return d


def _perfil(idc: int, facturas: list[Comprobante], hoy: date, perfiles: dict) -> Perfil:
    p = perfiles.get(idc) or {}
    fijo = p.get("CicloDias")
    return Perfil(ciclo=fijo or aprender_ciclo([f.fecha for f in facturas], hoy), fijado=bool(fijo), sin_ciclo=bool(p.get("SinCiclo")),
                  margen=p.get("MargenDias"), dado_de_baja=bool(p.get("DadoDeBaja")))


def _comp(c: Comprobante | None) -> dict | None:
    return c and {"idDeuda": c.id_deuda, "numero": c.numero, "fecha": c.fecha.isoformat(), "importe": round(c.importe, 2),
                  "cantidad": c.cantidad}


def tablero(hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    d = _datos()
    items, resumen = [], {"llego": 0, "pendiente": 0, "atrasada": 0, "baja": 0}
    descartadas = repo.descartadas()
    desde = hoy - timedelta(days=MESES_HISTORICO * 30)
    for idc, nombre in d["provs"].items():
        facturas = [Comprobante(fecha=x["fecha"], importe=x["importe"], numero=x["numero"] or "", id_deuda=x["idDeuda"])
                    for x in d["docs"][idc] if x["tipo"] == "Factura" and x["fecha"] <= hoy]
        perfil = _perfil(idc, facturas, hoy, d["perfiles"])
        r = evaluar(facturas, perfil, hoy, desde)
        if not r.actual:
            continue
        a = r.actual
        resumen[a.estado] += 1
        pago = None
        if a.estado == "atrasada":
            p = [x for x in d["pagos"][idc] if a.desde <= x["fecha"] <= hoy and (x["medio"], x["idOrigen"]) not in d["aplicados"]]
            pago = p and {"origen": p[-1]["medio"], "idPago": p[-1]["idOrigen"], "fecha": p[-1]["fecha"].isoformat(), "importe": p[-1]["importe"]}
        items.append({
            "idContacto": idc, "proveedor": nombre, "ciclo": CICLOS[r.ciclo], "cicloFijado": perfil.fijado, "estado": a.estado,
            "periodoDesde": a.desde.isoformat(), "periodoHasta": a.hasta.isoformat(), "fechaEsperada": a.esperada.isoformat(),
            "montoEsperado": a.monto_esperado, "cambioMonto": a.cambio_monto, "ultimo": _comp(agrupar(facturas)[-1] if facturas else None),
            "pagoSinComprobante": pago or None,
            "faltantesHistoricos": [{"clave": c, "periodoDesde": f.desde.isoformat(), "periodoHasta": f.hasta.isoformat(),
                                     "fechaEsperada": f.esperada.isoformat(), "montoEsperado": f.monto_esperado}
                                    for f in r.faltantes if (c := f"hist:{idc}:{f.esperada:%Y-%m}") not in descartadas],
        })
    orden = {"atrasada": 0, "baja": 1, "pendiente": 2, "llego": 3}
    items.sort(key=lambda i: (orden[i["estado"]], i["proveedor"]))
    return {"hoy": hoy.isoformat(), "items": items, "resumen": resumen}


def _alarmas(hoy: date) -> list[dict]:
    d = _datos()
    out = []
    marcados = {(m["origenPago"], m["idPago"]) for m in repo.marcas("abierta")}
    for idc, pagos in d["pagos"].items():
        for p in pagos:
            if p["fecha"] < DESDE_PAGOS or (p["medio"], p["idOrigen"]) in d["aplicados"] or (p["medio"], p["idOrigen"]) in marcados:
                continue
            # Señal fuerte: ningún comprobante del proveedor cerca del pago (los pagos parciales o a cuenta no son alarma).
            if any(abs((f - p["fecha"]).days) <= VENTANA_PAGO for f in d["deudas"][idc]):
                continue
            out.append({"clave": f"pago:{p['medio']}:{p['idOrigen']}", "tipo": "pago-sin-factura", "idContacto": idc,
                        "fecha": p["fecha"].isoformat(), "importe": round(p["importe"], 2),
                        "detalle": "Pago sin ningún comprobante del proveedor en ±60 días", "origen": {"medio": p["medio"], "id": p["idOrigen"]}})
    for idc, s in d["saldos"].items():
        if idc in d["provs"] and (s["saldo"] or 0) > 1 and s["ultima"] and (hoy - _dia(s["ultima"])).days > SALDO_A_FAVOR_DIAS:
            out.append({"clave": f"saldo:{idc}:{round(s['saldo'], 2)}", "tipo": "saldo-a-favor", "idContacto": idc,
                        "fecha": _dia(s["ultima"]).isoformat(), "importe": round(s["saldo"], 2),
                        "detalle": "Saldo a favor sin movimientos hace más de 90 días", "origen": None})
    for r in d["retenciones"]:
        idc = r["idContacto"]
        if idc not in d["provs"] or not r["fecha"]:
            continue
        f = _dia(r["fecha"])
        if not any(abs((x["fecha"] - f).days) <= RETENCION_DIAS for x in d["docs"][idc]):
            out.append({"clave": f"ret:{r['id']}", "tipo": "retencion-sin-factura", "idContacto": idc, "fecha": f.isoformat(),
                        "importe": round(float(r["importe"] or 0), 2), "detalle": f"Retención {r['numero'] or ''} sin factura en ±30 días".strip(),
                        "origen": {"medio": "retenciones", "id": r["id"]}})
    for r in d["remitos"]:
        idc = r["idContacto"]
        f = _dia(r["fecha"])
        if idc in d["provs"] and (hoy - f).days > REMITO_DIAS:
            out.append({"clave": f"remito:{r['id']}", "tipo": "remito-sin-factura", "idContacto": idc, "fecha": f.isoformat(), "importe": None,
                        "detalle": f"Remito {r['numero'] or ''} sin factura después de 60 días".strip(), "origen": {"medio": "remitos", "id": r["id"]}})
    descartadas = repo.descartadas()
    nombres = d["provs"]
    return [{**a, "proveedor": nombres[a["idContacto"]]} for a in out if a["clave"] not in descartadas]


def alarmas(tipo: str | None, page: int, page_size: int, hoy: date | None = None) -> dict:
    todas = sorted(_alarmas(hoy or date.today()), key=lambda a: a["fecha"], reverse=True)
    if tipo:
        todas = [a for a in todas if a["tipo"] == tipo]
    ini = (page - 1) * page_size
    return {"items": todas[ini: ini + page_size], "total": len(todas), "page": page, "pageSize": page_size}


def descartar(clave: str, motivo: str, usuario: str) -> None:
    if clave.startswith("hist:"):
        idc = int(clave.split(":")[1])
        if idc not in _datos()["provs"]:
            raise LookupError("La alarma no existe o ya fue resuelta.")
        repo.descartar(clave, idc, motivo, usuario)
        invalidar()
        return
    a = next((x for x in _alarmas(date.today()) if x["clave"] == clave), None)
    if a is None:
        raise LookupError("La alarma no existe o ya fue resuelta.")
    repo.descartar(clave, a["idContacto"], motivo, usuario)
    invalidar()


def cerrar_marcas_con_factura() -> int:
    """Una marca abierta se cierra sola con una factura del proveedor posterior (±60 días) y de importe compatible."""
    d = _datos()
    cerradas = 0
    for m in repo.marcas("abierta"):
        ref = _dia(m["periodoDesde"]) if m["periodoDesde"] else _dia(m["fechaAlta"])
        for x in d["docs"][m["idContacto"]]:
            if x["tipo"] != "Factura" or abs((x["fecha"] - ref).days) > VENTANA_PAGO:
                continue
            aprox = float(m["importeAprox"] or 0)
            if not aprox or abs(x["importe"] - aprox) <= 0.3 * aprox:
                repo.cerrar_marca(m["idMarca"], x["idDeuda"])
                cerradas += 1
                break
    return cerradas


def marcas(estado: str | None) -> list[dict]:
    cerrar_marcas_con_factura()
    nombres = _datos()["provs"]
    return [{**m, "proveedor": nombres.get(m["idContacto"], "")} for m in repo.marcas(estado)]


def crear_marca(body: dict, usuario: str) -> int:
    if any(m["origenPago"] == body["origenPago"] and m["idPago"] == body["idPago"] for m in repo.marcas("abierta")):
        raise ValueError("Ese pago ya está marcado como falta factura.")
    id_marca = repo.crear_marca(body, usuario)
    invalidar()
    return id_marca


def resumen_mensual(hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    fin_mes_anterior = hoy.replace(day=1) - timedelta(days=1)
    t = tablero(hoy)
    atrasadas = [i for i in t["items"] if i["estado"] == "atrasada" and i["fechaEsperada"] <= fin_mes_anterior.isoformat()]
    return {"mostrar": hoy.day >= 5 and bool(atrasadas), "mes": fin_mes_anterior.strftime("%Y-%m"), "atrasadas": len(atrasadas),
            "proveedores": [i["proveedor"] for i in atrasadas][:10]}


def pago_sin_factura(origen: str, id_pago: int) -> dict:
    sin_aplicar = (origen, id_pago) not in repo.pagos_aplicados()
    marcado = any(m["origenPago"] == origen and m["idPago"] == id_pago for m in repo.marcas("abierta"))
    return {"sinAplicar": sin_aplicar, "puedeMarcar": sin_aplicar and not marcado}
