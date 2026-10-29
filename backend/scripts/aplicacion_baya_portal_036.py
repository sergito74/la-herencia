"""036 — grupo 1, Bayá Casal (226): imputaciones copiadas de los recibos (RI) y aplicaciones (CA) de la extranet.

Regla de oro (Sergio 28/10/2026): una cuenta con resumen del proveedor se imputa como ese resumen, sin FIFO.
Fuente: `baya_aplicaciones_bajar_036` + `baya_aplicaciones_parsear_036` → backups/baya-aplicaciones-20261029/.
Cada RI o CA es un grupo: sus créditos (depósito/e-cheq/tarjeta del RI, retención RG, liquidación de granos LC,
notas de crédito) cancelan los débitos que lista (facturas, ND), en ese orden. El sistema lleva sus propias ND/NC de
diferencia de cambio (cierre bimonetario del 20/10), así que el portal dice QUÉ cancela QUÉ y el importe sale de lo
abierto en el sistema. Los 7 comprobantes de 2021 sin PDF se toman de las filas de la cuenta (GRUPOS_2021).
Lo anterior al portal (saldos iniciales al 30/04/2021 y antes) no tiene fuente del proveedor: queda por FIFO estricto,
rotulado. Reemplaza las aplicaciones activas de la cuenta. No toca saldos.
Uso (desde backend/): python -m scripts.aplicacion_baya_portal_036 [--aplicar]
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.recalculo_fifo import cambio, entrada, motor
from src.features.recalculo_fifo.ejecuciones import _filas_a_escribir
from src.features.vinculos.backup import backup_verificado

C, U = 226, "Sergio (barrida 036)"
NOTA = "Aplicación de Bayá Casal según recibos y aplicaciones de su extranet — barrida 036 29/10/2026"
CARPETA = Path(__file__).resolve().parents[2] / "backups" / "baya-aplicaciones-20261029"
TODO = 1e12  # en un grupo, cada par crédito→débito aplica lo que quede abierto de los dos

# Comprobantes de 2021 sin PDF: leídos de las filas de la cuenta con aplicaciones (observaciones del portal).
GRUPOS_2021 = [
    ("RI 888 23/04/2021", "23/04/2021", ["RI 0006 00000888"], ["FC 0020 00240846", "ND 0020 00063227"]),
    ("CA 4114 01/06/2021", "01/06/2021", ["RG 0001 00000005", "RI 0006 00002709", "NC 0020 00077711"],
     ["FC 0020 00231705", "FC 0020 00231707", "FC 0020 00237394"]),
    ("CA 5213 11/06/2021", "11/06/2021", ["RG 0001 00000009", "RI 0006 00003209", "NC 0020 00078177"], ["FC 0020 00250734"]),
    ("CA 7428 02/07/2021", "02/07/2021", ["NC 0020 00078434", "NC 0020 00078448"], ["FC 0020 00251640", "FC 0020 00251611"]),
    ("CA 7430 02/07/2021", "02/07/2021", ["RI 0006 00003225", "NC 0020 00079316"], ["FC 0020 00250733"]),
    ("CA 7479 02/07/2021", "02/07/2021", ["RI 0006 00003114"], ["FC 0020 00219332"]),
    ("CA 7480 02/07/2021", "02/07/2021", ["RI 0006 00003114"], ["FC 0020 00250733", "FC 0020 00251640"]),
]
# El RD 6-136157 es la refacturación de la FC 416539 (observaciones de las CA 145717 y 146076).
EQUIVALE = {"RD 0006 00136157": "FC 0020 00416539", "CA 0006 00053679": "RI 0006 00003114"}


def _dig(s) -> str:
    return re.sub(r"\D", "", str(s or ""))


def _f(s: str) -> date:
    return datetime.strptime(s, "%d/%m/%Y").date()


def grupos() -> list[tuple[str, date, list[str], list[str]]]:
    salida = [(n, _f(f), cr, db) for n, f, cr, db in GRUPOS_2021]
    for c in json.load(open(CARPETA / "aplicaciones.json", encoding="utf-8")):
        aplic = [a["comp"] for a in c["aplicacion"] if a["comp"] != "Anticipo"]
        if not aplic:
            continue  # todo a anticipo: lo aplica la CA que lo usa como origen
        if c["tipo"] == "RI":
            ri = "RI " + c["nro"]
            creditos = [ri] + [a["comp"] for a in c["aplicacion"] if a["comp"].startswith("NC")]
        else:
            creditos = [o["comp"] for o in c["origen"]] + [a["comp"] for a in c["aplicacion"] if a["comp"].startswith("NC")]
        debitos = [x for x in aplic if not x.startswith("NC")]
        salida.append((f"{c['tipo']} {c['nro']} {c['fecha']}", _f(c["fecha"]), creditos, debitos))
    return sorted(salida, key=lambda g: g[1])


def mapa(items: list[dict]) -> dict[str, list[tuple]]:
    """Comprobante del portal → claves del sistema."""
    por = defaultdict(list)
    docs = [i for i in items if i["clave"][0] == "Compras"]
    for i in docs:
        if (d := _dig(i["nro"])) and len(d) >= 5:
            por[d[-8:].lstrip("0")].append(tuple(i["clave"])[:2])
    comps = json.load(open(CARPETA / "aplicaciones.json", encoding="utf-8"))
    ri = {"RI " + c["nro"]: c for c in comps if c["tipo"] == "RI"}
    rg_imp = {}
    for c in comps:  # RG del origen de las CA: importe en la fila de origen
        for o in c["origen"]:
            if o["comp"].startswith("RG"):
                rg_imp[o["comp"]] = o["aCancelar"]
    rg_imp.update({"RG 0001 00000005": 7990.19, "RG 0001 00000009": 48695.91})
    # RG que viajan dentro de un RI (retenciones del recibo)
    rg_de_ri = {k: v["retenciones"] for k, v in ri.items() if v["retenciones"]}
    ri_2021 = {"RI 0006 00000888": (date(2021, 4, 23), None), "RI 0006 00002709": (date(2021, 6, 1), 747813.12),
               "RI 0006 00003114": (date(2021, 6, 9), 504278.14), "RI 0006 00003209": (date(2021, 6, 11), 2921755.36),
               "RI 0006 00003225": (date(2021, 6, 11), 231679.4)}
    pagos = [i for i in items if i["clase"] == "dinero" and i["lado"] == "C" and i["clave"][0] != "Retenciones"]
    rets = [i for i in items if i["clave"][0] == "Retenciones"]
    usados = set()

    def pago(fecha: date, importe: float | None) -> list[tuple]:
        cand = sorted((p for p in pagos if tuple(p["clave"])[:2] not in usados), key=lambda p: abs((p["fecha"] - fecha).days))
        if importe is None:  # RI 888: el depósito BNA del día
            elegido = [p for p in cand if p["fecha"] == fecha][:1]
        else:
            elegido = [p for p in cand if abs(float(p["importe"]) - importe) < 0.5][:1]
            if not elegido:  # un RI que junta dos pagos (p. ej. RI 46164 = Galicia 2580 + 2581)
                for a in cand[:12]:
                    for b in cand[:12]:
                        if a is not b and abs(float(a["importe"]) + float(b["importe"]) - importe) < 0.5:
                            elegido = [a, b]
                            break
                    if elegido:
                        break
        for p in elegido:
            usados.add(tuple(p["clave"])[:2])
        return [tuple(p["clave"])[:2] for p in elegido]

    def ret(importe: float, consumir: bool = True) -> list[tuple]:
        for r in rets:
            k = tuple(r["clave"])[:2]
            if (k not in usados or not consumir) and abs(float(r["importe"]) - importe) < 0.01:
                usados.add(k)
                return [k]
        return []

    resultado = {}
    for k, (fecha, imp) in ri_2021.items():
        resultado[k] = pago(fecha, imp)
    for k, c in ri.items():
        if k not in resultado and c["valores"]:
            resultado[k] = pago(_f(c["fecha"]), c["valores"])
        elif k not in resultado:
            resultado[k] = []
        if k in rg_de_ri:
            resultado[k] += ret(rg_de_ri[k])
    for k, imp in rg_imp.items():  # la misma retención que ya trae su RI (un RG puede ser origen de una CA)
        resultado[k] = ret(imp, consumir=False)
    # RI 46160: recibo solo de retenciones, una por factura (31.289,02 → FC 373600; 50.650,15 → FC 373633)
    resultado["RI 0006 00046160"] = ret(31289.02) + ret(50650.15)
    resultado["_por_numero"] = por
    return resultado


def _fila(a: dict) -> dict:
    """Aplicación del motor con las claves que espera `_filas_a_escribir`."""
    return {"oc": a["credito"][0], "ic": a["credito"][1], "od": a["debito"][0], "id_": a["debito"][1],
            "ars": a["importeArs"], "dif": a["diferenciaCambio"], "regla": a["regla"]}


def resolver(comp: str, m: dict) -> list[tuple]:
    comp = EQUIVALE.get(comp, comp)
    if comp in m:
        return m[comp]
    tipo, _pv, nro = comp.split()
    if tipo == "LC":
        return [k for d, ks in m["_por_numero"].items() for k in ks if False] or \
            [("Venta Granos", r["i"]) for r in fetch_all(
                "SELECT IdOrigen AS i FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ? AND Origen = 'Venta Granos' "
                "AND [Nro Documento] LIKE ?", (C, "%" + _pv[-2:] + nro))]
    return m["_por_numero"].get(nro.lstrip("0"), [])


if __name__ == "__main__":
    _assert_target_is_wc()
    hoy = date.today()
    tc = cambio.funcion_tc(hoy)
    e = entrada.armar([C])[C]
    # La vista trae el importe de los documentos en us$ ya pesificado al TC del comprobante; el motor lo espera en us$.
    for i in e["items"]:
        if i["moneda"] == "USD" and i.get("tcDoc"):
            i["importe"] = round(float(i["importe"]) / i["tcDoc"], 2)
    m = mapa(e["items"])
    fijos, sin = [], []
    for nombre, fecha, creditos, debitos in grupos():
        cr = [(c, k) for c in creditos for k in resolver(c, m)]
        db = [(d, k) for d in debitos for k in resolver(d, m)]
        sin += [(nombre, c) for c in creditos + debitos if not resolver(c, m)]
        for _, kc in cr:
            for _, kd in db:
                fijos.append({"credito": kc, "debito": kd, "importe": TODO, "regla": "manual", "grupo": nombre})
    res = motor.recalcular(e["items"], fijos, tc, hoy)
    por_grupo = defaultdict(float)
    print("Grupos:", len(grupos()), " pares:", len(fijos))
    print("Comprobantes del portal sin equivalente en el sistema:")
    for x in sin:
        print("  ", x)
    reglas = defaultdict(lambda: [0, 0.0])
    for a in res["aplicaciones"]:
        reglas[a["regla"]][0] += 1
        reglas[a["regla"]][1] += a["importeArs"]
    print("Aplicaciones por regla:", {k: (v[0], round(v[1], 2)) for k, v in reglas.items()})
    abiertos = [(i["clave"][1], i["nro"], i["fecha"], round(i["rem"], 2), i["moneda"]) for i in res["items"]
                if i["rem"] > 0.01 and i["clase"] == "doc" and i["lado"] == "D"]
    print("Documentos abiertos:", len(abiertos))
    for x in abiertos:
        print("  ", x)
    dinero = [(i["clave"], i["fecha"], round(i["rem"], 2)) for i in res["items"] if i["rem"] > 0.01 and i["lado"] == "C"]
    print("Créditos con resto:", dinero)
    if "--salida" in sys.argv:
        json.dump(res["aplicaciones"], open(sys.argv[sys.argv.index("--salida") + 1], "w", encoding="utf-8"), default=str, indent=1)
    if "--aplicar" not in sys.argv:
        raise SystemExit("Simulación: usar --aplicar para grabar.")
    print("Respaldo verificado:", backup_verificado("aplicacion-baya-portal-036"))
    antes = bimonetaria.cargar_cuenta(C, refrescar=True)
    stmts = [("UPDATE a SET Anulada = 1, MotivoAnulacion = ?, UsuarioAnulacion = ?, FechaAnulacion = SYSDATETIME() "
              "FROM dbo.AplicacionesPago a JOIN dbo.Compras c ON c.IdDeuda = a.IdDocumentoAplicado "
              "WHERE c.IdContacto = ? AND a.TipoDocumento = 'CompraDeuda' AND a.Anulada = 0",
              ("Reemplazada por las aplicaciones de la extranet de Bayá Casal (barrida 036)", U, C))]
    stmts += [("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, "
               "ImporteAplicado, Fecha, Usuario, Anulada, Origen, NotaConciliacion) VALUES (?, ?, ?, ?, ?, SYSDATETIME(), ?, 0, ?, ?)",
               (f[0], f[1], f[2], f[3], f[4], U, "manual" if f[5] == "manual" else "fifo-032",
                NOTA if f[5] == "manual" else "Bayá Casal antes de la extranet (sin fuente del proveedor): FIFO estricto — barrida 036"))
              for a in res["aplicaciones"] for f in _filas_a_escribir([_fila(a)])]
    execute_write_transaction(stmts)
    bimonetaria.invalidar()
    despues = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("Saldo antes:", antes["saldoPesos"], antes["saldoDolares"], " después:", despues["saldoPesos"], despues["saldoDolares"])
