"""036 — Cargill (258), 29/10/2026: imputaciones copiadas de los avisos de pago del portal de Cargill.

Regla de oro (Sergio 28-29/10/2026): Cargill se imputa exactamente como lo tiene cargado en su sistema, sin FIFO.
Fuente: los avisos de pago del portal (`cargill_avisos_parsear_036` → backups/cargill-aplicaciones-20261029/avisos.json),
que listan qué documentos cancela cada cobro/netting. Dentro de cada aviso los créditos (LPG, NC, cobro con tarjeta)
cancelan los débitos (facturas, ND, anticipos, ajustes) del mismo aviso, en el orden del aviso.
Antes de 2021 (no hay avisos) aplica la regla aprobada el 29/10/2026 respetando los pendientes que informó Cargill
en sus estados de cuenta por mail (`tramo_previo`).
Reemplaza las aplicaciones activas de la cuenta (198 de la corrida 020). No toca ValuacionProveedor ni saldos.

Uso (desde backend/): python -m scripts.aplicacion_cargill_avisos_036 [--aplicar]
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from itertools import combinations
from collections import defaultdict
from pathlib import Path

import openpyxl

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C, U = 258, "Sergio (barrida 036)"
NOTA = "Aplicación de Cargill según avisos de pago del portal — barrida 036 29/10/2026"
AVISOS = Path(__file__).resolve().parents[2] / "backups" / "cargill-aplicaciones-20261029" / "avisos.json"
MEDIO = {"Venta Granos": "comp-venta-granos", "Compras": "comp-compra", "Tarjetas": "tarjetas", "Pagos efectivo": "efectivo",
         "Galicia": "galicia", "Banco Nacion": "bna", "Pagos Valores Recibidos": "valores-recibidos"}
PAGOS = ("Galicia", "Banco Nacion", "Tarjetas", "Pagos Valores Recibidos", "Compras")  # Compras: ajuste AJ en NC


def _dig(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


def _clave_fila(f: dict):
    n = re.sub(r"\s*\(\d+\)$", "", f["numeroDocumento"] or "")   # LPG partida en dos: "330125575215 (1)"
    if f["origenTipo"] == "Compras" and re.match(r"^\d+-\d+$", n):
        pv, num = n.split("-")
        return ("C", int(pv), int(num))
    return ("N", _dig(n).lstrip("0")) if _dig(n) else None


def _clave_aviso(d: dict):
    n = d["numero"] or ""
    if d["tp"] in ("RI", "RT", "RM") and len(n) == 12 and n.isdigit():
        return ("C", int(n[:4]), int(n[4:]))
    return ("N", _dig(n).lstrip("0")) if _dig(n) else None


POR_IMPORTE = ("AH", "X&", "X@", "H7", "D&", "V4", "RI", "RT", "H9")


def _pago(filas: list[dict], resto: dict, importe: float, fecha) -> list[tuple]:
    """Recibo (RU) o cobro con tarjeta (Q#): nuestro pago, ±30 días. Devuelve [(clave, tope)].
    1) un pago por el importe (±$1, la tarjeta difiere en centavos); 2) líneas de tarjeta que suman el
    importe; 3) un pago mayor que cubre varios recibos (Galicia 28/05/2026 = RU 30/05 + RU 10/06)."""
    cand = [f for f in filas if f["origenTipo"] in PAGOS and resto.get((f["origenTipo"], f["idOrigen"]), 0) >= 0.01
            and f["fecha"] and abs((f["fecha"] - fecha).days) <= 30]
    clave = lambda f: (f["origenTipo"], f["idOrigen"])
    uno = sorted([f for f in cand if abs(resto[clave(f)] - importe) <= 1], key=lambda f: abs((f["fecha"] - fecha).days))
    if uno:
        return [(clave(uno[0]), None)]
    tarjetas = [f for f in cand if f["origenTipo"] == "Tarjetas"]
    for n in range(2, min(len(tarjetas), 6) + 1):
        for grupo in combinations(tarjetas, n):
            if abs(sum(resto[clave(f)] for f in grupo) - importe) <= 1:
                return [(clave(f), None) for f in grupo]
    mayor = sorted([f for f in cand if resto[clave(f)] > importe], key=lambda f: abs((f["fecha"] - fecha).days))
    return [(clave(mayor[0]), importe)] if mayor else []


def _por_importe(filas: list[dict], importe: float, fecha, usados: set) -> list[dict]:
    """Movimiento de la cuenta con ese importe exacto (en pesos o en la moneda original: redondeos H9 en US$), el más cercano en fecha (hasta 400 días antes del aviso)."""
    cand = [f for f in filas if (f["origenTipo"], f["idOrigen"]) not in usados
            and min(abs(round(v - importe, 2)) for v in (f["deudaPesos"] or f["creditoPesos"] or 0,
                                                         f["deudaOriginal"] or f["creditoOriginal"] or 0)) <= 0.01
            and f["fecha"] and -400 <= (f["fecha"] - fecha).days <= 30]
    return sorted(cand, key=lambda f: abs((f["fecha"] - fecha).days))[:1]


CORTE = date(2021, 1, 8)            # primer aviso del portal
ESTADOS = Path(__file__).resolve().parents[2] / "backups" / "cargill-conciliacion-20261020" / "mails"


def pendientes_cargill() -> list[tuple]:
    """(fecha, clave doc) de los "Estado de cuenta Bolívar" que Cargill mandó por mail (oct-2019 a ago-2021)."""
    salida = []
    for f in sorted(ESTADOS.glob("*Estado de cuenta Bol*.xlsx")):
        fecha = datetime.strptime(f.name[:8], "%Y%m%d").date()
        for ws in openpyxl.load_workbook(f, data_only=True).worksheets:
            for r in ws.iter_rows(values_only=True):
                if r and r[0] in ("FC", "ND", "NC") and r[1]:
                    n = str(r[1]).strip()
                    if "-" in n:
                        pv, num = n.split("-")
                    else:
                        n = n.zfill(14)
                        pv, num = n[2:6], n[6:]
                    salida.append((fecha, ("C", int(pv), int(num))))
    return salida


def tramo_previo(filas: list[dict], cap: dict, resto: dict) -> list[tuple]:
    """Antes de 2021 no hay avisos: regla aprobada 29/10/2026 (sección 12 de la auditoría) — importe idéntico, luego
    combinación de 2-3 facturas, luego FIFO que no salta más de un ciclo; nunca cancela antes de tiempo un documento que
    Cargill informó pendiente en sus estados de cuenta."""
    bloqueos = defaultdict(list)
    for fecha, k in pendientes_cargill():
        bloqueos[k].append(fecha)
    debitos = sorted([f for f in filas if f["origenTipo"] == "Compras" and f["fecha"] and f["fecha"] < CORTE
                      and cap.get(("Compras", f["idOrigen"]), 0) >= 0.01], key=lambda f: (f["fecha"], f["numeroDocumento"]))
    creditos = sorted([f for f in filas if f["fecha"] and f["fecha"] < CORTE and f["origenTipo"] in MEDIO
                       and resto.get((f["origenTipo"], f["idOrigen"]), 0) >= 0.01], key=lambda f: f["fecha"])
    kd = lambda f: ("Compras", f["idOrigen"])
    kc = lambda f: (f["origenTipo"], f["idOrigen"])
    bloqueado = lambda cr, db: any(s >= cr["fecha"] for s in bloqueos.get(_clave_fila(db), []))
    salida = []

    def aplicar(cr, db, regla, tope=None):
        x = round(min(resto[kc(cr)], cap[kd(db)], tope if tope is not None else resto[kc(cr)]), 2)
        if x >= 0.01:
            salida.append((f"previo-2021 {regla}", cr["origenTipo"], cr["idOrigen"], db["idOrigen"], x))
            resto[kc(cr)] = round(resto[kc(cr)] - x, 2)
            cap[kd(db)] = round(cap[kd(db)] - x, 2)

    abiertos = lambda: [d for d in debitos if cap[kd(d)] >= 0.01]
    for cr in creditos:                                    # 1) importe idéntico
        importe = resto[kc(cr)]
        iguales = [d for d in abiertos() if abs(cap[kd(d)] - importe) <= 0.01 and cap[kd(d)] == round(d["deudaPesos"], 2)]
        if not iguales or len(iguales) >= 3 or any(bloqueado(cr, d) for d in iguales[:1]):
            continue
        elegido = sorted(iguales, key=lambda d: (abs((d["fecha"] - cr["fecha"]).days), d["fecha"] > cr["fecha"],
                                                  d["numeroDocumento"]))[0]
        if not bloqueado(cr, elegido):
            aplicar(cr, elegido, "importe-identico")
    for cr in creditos:                                    # 2) combinación única de 2 o 3 facturas
        if resto[kc(cr)] < 0.01:
            continue
        cand = [d for d in abiertos() if abs((d["fecha"] - cr["fecha"]).days) <= 365 and not bloqueado(cr, d)][:25]
        combos = [g for n in (2, 3) for g in combinations(cand, n)
                  if abs(sum(cap[kd(d)] for d in g) - resto[kc(cr)]) <= 0.01]
        if len(combos) == 1:
            for d in combos[0]:
                aplicar(cr, d, "combinacion")
    for cr in creditos:                                    # 3) FIFO hasta un ciclo (30 días) después del crédito
        for d in abiertos():
            if resto[kc(cr)] < 0.01 or (d["fecha"] - cr["fecha"]).days > 30:
                break
            if not bloqueado(cr, d):
                aplicar(cr, d, "fifo")
    return salida


if __name__ == "__main__":
    aplicar_cambios = "--aplicar" in sys.argv
    _assert_target_is_wc()
    filas = bimonetaria.cargar_cuenta(C, refrescar=True)["filas"]
    avisos = json.load(open(AVISOS, encoding="utf-8"))

    por_clave: dict[tuple, list[dict]] = defaultdict(list)
    for f in filas:
        k = _clave_fila(f)
        if k:
            por_clave[k].append(f)
    # capacidad en pesos de cada débito (documento de Compras) y de cada crédito
    cap = {("Compras", f["idOrigen"]): f["deudaPesos"] for f in filas if f["origenTipo"] == "Compras" and f["deudaPesos"]}
    resto = {(f["origenTipo"], f["idOrigen"]): f["creditoPesos"] for f in filas if f["creditoPesos"] and f["origenTipo"] in MEDIO}

    usados: set = set()
    asignaciones: list[tuple] = []           # (aviso, origen crédito, id crédito, id doc, pesos)
    sin_match, sobrantes, faltantes = [], [], []
    anticipos: list[dict] = []   # V4: anticipo financiero que Cargill desembolsó neteando débitos del mismo aviso
    for a in avisos:
        debitos, creditos, v4, ah = [], [], [], []
        for d in a["documentos"]:
            k = _clave_aviso(d)
            cand = por_clave.get(k, []) if k else []
            if d["tp"] in ("RU", "Q#"):
                pagos = _pago(filas, resto, abs(d["importe"]), datetime.strptime(a["fecha"], "%d/%m/%Y").date())
                if pagos:
                    creditos += pagos
                    continue
            if not cand and d["tp"] in POR_IMPORTE:   # sin número en el aviso: importe exacto, fecha más cercana
                cand = _por_importe(filas, abs(d["importe"]), datetime.strptime(a["fecha"], "%d/%m/%Y").date(), usados)
            if not cand:
                if d["tp"] == "V4":
                    v4.append(d["importe"])
                elif d["tp"] == "AH":
                    ah.append(d["importe"])
                if d["tp"] not in ("$I", "$B"):   # las retenciones están dentro de la LPG
                    sin_match.append((a["voucher"], a["fecha"], d["tp"], d["numero"], d["importe"]))
                continue
            for f in cand:
                usados.add((f["origenTipo"], f["idOrigen"]))
                clave = (f["origenTipo"], f["idOrigen"])
                if clave in cap and clave not in [c for c, _ in debitos]:
                    debitos.append([clave, abs(d["importe"])])   # tope: lo que Cargill cancela de ese documento
                elif clave in resto and clave not in [c for c, _ in creditos]:
                    creditos.append((clave, None))
        # AH: Cargill cancela un anticipo V4 anterior; los débitos neteados en ese desembolso se cancelan ahora
        for importe in ah:
            for ant in anticipos:
                if ant["monto"] >= importe - 0.01:
                    ant["monto"] = round(ant["monto"] - importe, 2)
                    debitos += [db for db in ant["debitos"] if db[1] >= 0.01 and db not in debitos]
                    break
        creditos = [[cr, tope] for cr, tope in creditos]

        def asignar(cr, db):
            x = round(min(resto[cr[0]], cap[db[0]], db[1], cr[1] if cr[1] is not None else resto[cr[0]]), 2)
            if x >= 0.01:
                asignaciones.append((a["voucher"], cr[0][0], cr[0][1], db[0][1], x))
                resto[cr[0]] = round(resto[cr[0]] - x, 2)
                cap[db[0]] = round(cap[db[0]] - x, 2)
                db[1] = round(db[1] - x, 2)
                if cr[1] is not None:
                    cr[1] = round(cr[1] - x, 2)

        for cr in creditos:                   # primero los pares de importe idéntico (línea de tarjeta ↔ factura)
            for db in debitos:
                if db[1] >= 0.01 and abs(min(resto[cr[0]], cr[1] if cr[1] is not None else resto[cr[0]]) - db[1]) <= 0.01:
                    asignar(cr, db)
                    break
        for cr in creditos:
            for db in debitos:
                asignar(cr, db)
        if v4:
            anticipos.append({"monto": round(sum(v4), 2), "debitos": [db for db in debitos if db[1] >= 0.01]})
        faltantes += [(a["voucher"], db[0][1], cap[db[0]]) for db in debitos if db[1] >= 0.01]

    asignaciones += tramo_previo(filas, cap, resto)

    print("Avisos:", len(avisos), " imputaciones:", len(asignaciones), " pesos:", round(sum(x[4] for x in asignaciones), 2))
    print("Documentos del aviso que no están en el sistema:")
    for x in sin_match:
        print("  ", x)
    print("Débitos de avisos que quedaron sin cubrir dentro del aviso (bancos/anticipos los cubren):", len(faltantes),
          round(sum(x[2] for x in faltantes), 2))
    doc_sin = [(f["numeroDocumento"], f["fecha"], round(cap[("Compras", f["idOrigen"])], 2)) for f in filas
               if ("Compras", f["idOrigen"]) in cap and cap[("Compras", f["idOrigen"])] >= 0.01]
    print("Documentos de Compras sin aplicación de Cargill:", len(doc_sin), round(sum(x[2] for x in doc_sin), 2))
    print("Créditos con resto sin aplicar:", sum(1 for v in resto.values() if v >= 0.01), round(sum(v for v in resto.values() if v >= 0.01), 2))
    actuales = fetch_all("SELECT COUNT(*) AS n FROM dbo.AplicacionesPago a JOIN dbo.Compras c ON c.IdDeuda = a.IdDocumentoAplicado "
                         "WHERE c.IdContacto = ? AND a.TipoDocumento = 'CompraDeuda' AND a.Anulada = 0", (C,))[0]["n"]
    print("Aplicaciones activas que se anulan:", actuales)
    salida = Path(sys.argv[sys.argv.index("--salida") + 1]) if "--salida" in sys.argv else None
    if salida:
        json.dump({"asignaciones": asignaciones, "sin_match": sin_match, "faltantes": faltantes, "doc_sin": doc_sin},
                  open(salida, "w", encoding="utf-8"), default=str, ensure_ascii=False, indent=1)
    if not aplicar_cambios:
        print("Simulación: usar --aplicar para grabar.")
        raise SystemExit
    print("Respaldo verificado:", backup_verificado("aplicacion-cargill-avisos-036"))
    antes = bimonetaria.cargar_cuenta(C, refrescar=True)
    stmts = [("UPDATE a SET Anulada = 1, MotivoAnulacion = ?, UsuarioAnulacion = ?, FechaAnulacion = SYSDATETIME() "
              "FROM dbo.AplicacionesPago a JOIN dbo.Compras c ON c.IdDeuda = a.IdDocumentoAplicado "
              "WHERE c.IdContacto = ? AND a.TipoDocumento = 'CompraDeuda' AND a.Anulada = 0",
              ("Reemplazada por la aplicación de los avisos de Cargill (barrida 036)", U, C))]
    stmts += [("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, "
               "ImporteAplicado, Fecha, Usuario, Anulada, Origen, NotaConciliacion) VALUES (?, ?, 'CompraDeuda', ?, ?, SYSDATETIME(), ?, 0, 'manual', ?)",
               (MEDIO[o], i, d, x, U, f"{NOTA} — aviso {v}")) for v, o, i, d, x in asignaciones]
    execute_write_transaction(stmts)
    bimonetaria.invalidar()
    despues = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("Saldo antes:", antes["saldoPesos"], antes["saldoDolares"], " después:", despues["saldoPesos"], despues["saldoDolares"])
