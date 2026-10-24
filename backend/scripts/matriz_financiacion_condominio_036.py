"""Matriz única de fuentes/representaciones; SOLO LECTURA, no calcula deuda de socio.

Los enlaces por importe/fecha se conservan como candidatos, nunca como prueba.
"""

import csv
import json
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal

from scripts.rastrear_15_pagos_condominio_036 import (
    HERENCIA,
    LSC,
    OUT,
    candidates,
    day,
    fingerprint,
    money,
    workbook,
)
from src.features.cajas_efectivo.operaciones import read


def run():
    source = LSC / "Movimientos LSC.xlsx"
    aportes = HERENCIA / "Administracion y gestion/Aportes de Capital Directores.xlsx"
    movs = workbook(source, "Movs")
    capital = workbook(aportes, "Depositos 1")
    camion = HERENCIA.parent / "Maignal/Pagos Venta Camion.xlsx"
    cheques = workbook(camion, "Cheques 3os")
    camion_evidence = [
        {"fila": i, "numero": r[0], "importe": money(r[5]), "destino": r[6]}
        for i, r in enumerate(cheques, 1)
        if r[0] in (87678128, 95512293)
    ]
    assert {r["numero"] for r in camion_evidence} == {87678128, 95512293}
    banks = read(
        "SELECT IdMovimientoBNA id,[Fecha / Hora Mov#] fecha,Importe importe,IdContacto contacto,"
        "Concepto concepto FROM dbo.[Movimientos BNA] WHERE [Fecha / Hora Mov#]>=? "
        "AND [Fecha / Hora Mov#]<?",
        ("20110101", "20160501"),
    )
    payments = read(
        "SELECT IdPagoEfectivo id,Fecha fecha,[Importe imputado] importe,IdContacto contacto,"
        "IdOperacion operacion,[Numero documento] numero,IdFormaPago medio "
        "FROM dbo.vw_PagosEfectivoVigentes WHERE Caja='Condominio' AND Fecha>=? AND Fecha<?",
        ("20110101", "20160401"),
    )
    cash = read(
        "SELECT IdMovimiento id,Caja caja,Fecha fecha,Importe importe,Concepto concepto,"
        "Detalle detalle,IdPagoEfectivo pago,IdOperacionCaja operacion,Anulada anulada "
        "FROM dbo.MovimientosCajaEfectivo WHERE Fecha>=? AND Fecha<?",
        ("20110101", "20160501"),
    )
    ledger = read(
        "SELECT * FROM dbo.MovimientosCuentaSocio WHERE IdSocio=3 ORDER BY Fecha,IdMovimiento"
    )
    historical = read(
        "SELECT IdMovimiento id,Fecha fecha,Importe importe,Concepto concepto "
        "FROM dbo.vw_MovimientosCajaEfectivoOperativos WHERE Caja='CondominioLSC' ORDER BY Fecha"
    )
    canonical = {}
    payment_keys = {}
    for i, r in enumerate(capital, 1):
        if not isinstance(r[3], (int, float)):
            continue
        key = f"APORTE-F{i}"
        amount = money(r[3])
        reference = str(r[2])
        route = (
            "devolucion"
            if amount < 0
            else "prestamo2016"
            if i == 61
            else "pago_directo_cheque"
            if i == 14
            else "efectivo"
            if i in (7, 21, 33)
            else "ruta_por_confirmar"
            if i == 8
            else "banco_segun_fuente"
        )
        entry = {
            "clave": key,
            "fecha": day(r[1]).isoformat(),
            "importeFuente": amount,
            "referencia": reference,
            "tipo": route,
            "fuentes": [f"Depositos 1!B{i}:D{i}"],
            "pagos": [],
            "cajas": [],
            "puentes": [],
            "bnaCandidatos": [],
            "socio": [],
            "estado": "financiacion_fuente_sin_asiento_individual_socio3",
        }
        # Solo registra candidatos bancarios de igual signo y valor, no asigna contactos.
        if route in ("banco_segun_fuente", "ruta_por_confirmar"):
            entry["bnaCandidatos"] = [
                x
                for x in candidates(banks, {"importe": abs(amount), "fecha": r[1]})
                if (x["importe"] > 0) == (amount > 0)
            ]
        # Relaciones estructurales conocidas, no deduplicación genérica por importe.
        if i == 14:
            p = next(x for x in payments if x["id"] == 290)
            assert int(p["numero"]) == 95512293 and money(p["importe"]) == amount
            assert day(p["fecha"]) == day(r[1])
            entry["pagos"].append(p["id"])
            payment_keys[p["id"]] = key
            entry["fuentes"] += ["Movs!A725:I726", "Aportes Campo!B15:D15"]
        if i in (7, 21, 33):
            match = [
                x
                for x in cash
                if x["caja"] == "GiamigliSA"
                and x["concepto"] == "Aporte efectivo Condominio LSC"
                and day(x["fecha"]) == day(r[1])
                and money(x["importe"]) == amount
            ]
            assert len(match) == 1
            entry["cajas"] += [x["id"] for x in match]
        if i == 61:
            assert any(x["id"] == 2129 and money(x["importe"]) == -amount for x in cash)
            entry["cajas"] += [2129]  # Condominio: salida préstamo documentado.
        if i == 62:
            assert any(x["id"] == 78 and money(x["importe"]) == amount for x in cash)
            entry["cajas"] += [78]  # Giamigli: devolución, no otro aporte.
        canonical[key] = entry
    assert len(canonical) == 61
    assert sum(r["importeFuente"] for r in canonical.values()) == Decimal("733781")
    source_expenses = []
    ambiguous = []
    for i, r in enumerate(movs, 1):
        if not isinstance(r[0], datetime) or not "20110101" <= r[0].strftime("%Y%m%d") < "20160401":
            continue
        if r[4] != "Compra Giamigli" or r[5] != "EF":
            continue
        matches = [
            x
            for x in payments
            if day(x["fecha"]) == day(r[0]) and money(x["importe"]) == money(r[8])
        ]
        source_expenses.append(
            {"fila": i, "importe": money(r[8]), "pagos": [x["id"] for x in matches]}
        )
        if len(matches) != 1:
            ambiguous.append({"fila": i, "candidatos": matches})
            continue
        p = matches[0]
        key = payment_keys.get(p["id"], f"PAGO-{p['id']}")
        if key not in canonical:
            canonical[key] = {
                "clave": key,
                "fecha": day(p["fecha"]).isoformat(),
                "importeFuente": money(p["importe"]),
                "referencia": r[2],
                "tipo": "pago_directo_segun_fuente",
                "fuentes": [],
                "pagos": [p["id"]],
                "cajas": [],
                "puentes": [],
                "bnaCandidatos": [],
                "socio": [],
                "estado": "pago_existente_titular_reintegro_por_validar",
            }
        canonical[key]["fuentes"].append(f"Movs!A{i}:I{i}")
        payment_keys[p["id"]] = key
    assert len(source_expenses) == 105
    assert sum(r["importe"] for r in source_expenses) == Decimal("110536.02")
    bycash = {x["id"]: x for x in cash}
    bridges = [
        x
        for x in cash
        if x["concepto"] == "Aporte Condominio LSC (pago directo)" and not x["anulada"]
    ]
    bridge_pending = []
    for bridge in bridges:
        match = re.search(r"egreso mov\. (\d+)", bridge["detalle"] or "")
        leg = bycash.get(int(match[1])) if match else None
        if not leg or money(bridge["importe"]) != -money(leg["importe"]):
            bridge_pending.append(bridge)
            continue
        key = payment_keys.get(leg["pago"])
        if not key:
            key = f"CAJA-EGRESO-{leg['id']}"
            canonical[key] = {
                "clave": key,
                "fecha": day(bridge["fecha"]).isoformat(),
                "importeFuente": money(bridge["importe"]),
                "referencia": bridge["detalle"],
                "tipo": "puente_caja_pendiente_validar_origen",
                "fuentes": [],
                "pagos": [],
                "cajas": [],
                "puentes": [],
                "bnaCandidatos": [],
                "socio": [],
                "estado": "par_caja_no_aporte_adicional_automatico",
            }
            if leg["pago"]:
                canonical[key]["pagos"].append(leg["pago"])
                payment_keys[leg["pago"]] = key
        canonical[key]["cajas"].append(leg["id"])
        canonical[key]["puentes"].append(bridge["id"])
    # No sumar de nuevo un crédito BNA a su aporte de planilla candidato.
    account = read(
        "SELECT * FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=549 ORDER BY Fecha,IdOrigen"
    )
    mappings = []
    for row in account:
        keys = (
            [
                r["clave"]
                for r in canonical.values()
                if any(b["id"] == row["IdOrigen"] for b in r["bnaCandidatos"])
            ]
            if row["Origen"] == "Banco Nacion"
            else []
        )
        mappings.append({"movimiento": row, "clavesCandidatas": keys})
    documentary = {
        333: "HSBC Condominio12/11/2012,RSBA,partida0079575; origen documentado, sin pago nuevo.",
        378: "HSBC Condominio11/03/2013,RSBA,partida0079575; origen documentado, sin pago nuevo.",
        190: "HSBC Oscar12/04/2011,DA95 Irma período03/2011; WC11/04. Patrimonio por confirmar.",
        191: "HSBC Oscar11/05/2011,DA95 Irma período04/2011; patrimonio por confirmar.",
        192: "HSBC Oscar13/06/2011,95 sin identificación fiscal; candidato bancario.",
        193: "HSBC Oscar08/08/2011,DA95 Irma período07/2011; patrimonio por confirmar.",
        194: "HSBC Oscar19/09/2011,DA95 Irma período08/2011; patrimonio por confirmar.",
        28: "Cheque87678128 Maignal2926 respaldado en dos libros; destino sin recibo de endoso.",
        290: "Cheque95512293 Maignal3031,siembra avena; incluido enAPORTE-F14.",
        315: "Factura1578 a cuenta corriente, sin voucher/resumen/titular identificado.",
        503: "Original2253.03 corregido; pago2253.04 conservado. Falta titular/resumen.",
        561: "Original1361.54 corregido; pago1250.97 conservado. Falta titular/resumen.",
        441: "Ticket efectivo175.03 más0.01; WC175.04 medio10. Falta fondeo/reintegro.",
        442: "Ticket efectivo204.44; WC medio10. Falta fondeo/reintegro.",
        467: "Ticket efectivo140.05; WC medio10. Falta fondeo/reintegro.",
    }
    for entry in canonical.values():
        entry["observacionesDocumentales"] = {
            str(p): documentary[p] for p in entry["pagos"] if p in documentary
        }
    return {
        "fecha": datetime.now().isoformat(),
        "modo": "solo_lectura_no_es_saldo",
        "fuentes": [fingerprint(p) for p in (source, aportes, camion)],
        "chequesMaignal": camion_evidence,
        "evidenciasExternas": {
            "ARBA333_378": "HSBC Condominio: 12/11/2012 y11/03/2013,10004.70 cada uno; "
            "servicioRSBA y partida0079575 coinciden. No importar otro pago.",
            "AFIP190_191_193_194": "HSBC titularOscar: 12/04,11/05,08/08,19/09/2011; "
            "DA95 identifica aIrma. Clasificación patrimonial pendiente de Sergio.",
            "AFIP192": "HSBC titularOscar13/06/2011:95, sin identificación del contribuyente "
            "en la línea. Candidato, no prueba fiscal completa.",
            "pago28": "Maignal/Cheques 3os fila8 y Pagos Venta Camion1/Pagos fila4: "
            "87678128,2926,25/10/2011. Origen del cheque respaldado; destino vacío.",
            "tarjetas315_503_561": "Sin resumen/titular de tarjeta localizado2012–2014. "
            "Easy yCooperativa originales corregidos, importes de pagos conservados.",
        },
        "operaciones": list(canonical.values()),
        "resumen": {
            "filasAportes": 61,
            "totalAportesNeto": Decimal("733781"),
            "pagosEF": len(source_expenses),
            "totalPagosEF": Decimal("110536.02"),
            "operacionesAportesYPagosSinDuplicarCheque": 165,
            "totalFuentesAportesYPagosSinDuplicarCheque": Decimal("841286.02"),
            "puentesCaja": len(bridges),
            "totalPuentesCaja": sum((x["importe"] for x in bridges), Decimal(0)),
            "puentesYaEnAportesOPagos": sum(
                bool(x["puentes"]) and x["tipo"] != "puente_caja_pendiente_validar_origen"
                for x in canonical.values()
            ),
            "restantesPuentesPendientes": sum(
                x["tipo"] == "puente_caja_pendiente_validar_origen" for x in canonical.values()
            ),
            "categorias": dict(Counter(x["tipo"] for x in canonical.values())),
        },
        "filasEF": source_expenses,
        "ambiguedadesEF": ambiguous,
        "puentesSinPar": bridge_pending,
        "cuenta549": mappings,
        "socio3Completo": ledger,
        "historicosCondominio31": historical,
        "saldoNominal549": sum((x["Credito"] - x["Deuda"] for x in account), Decimal(0)),
        "advertencia": "841286.02 es universo de fuentes, no deuda/asiento ni totalidad "
        "del Condominio. "
        "140 puentes no se suman sin contrastar su egreso y origen. Candidatos BNA no son enlaces "
        "confirmados; no sumarlos al aporte. 31 históricos posteriores se mantienen separados. "
        "No se agregaron asientos ni se valorizó kg/USD.",
    }


if __name__ == "__main__":
    report = run()
    OUT.mkdir(parents=True, exist_ok=True)
    base = OUT / f"matriz-financiacion-{datetime.now():%Y%m%d-%H%M%S}"
    base.with_suffix(".json").write_text(
        json.dumps(report, default=str, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with base.with_suffix(".csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = [
            "clave",
            "fecha",
            "importeFuente",
            "tipo",
            "referencia",
            "fuentes",
            "pagos",
            "cajas",
            "puentes",
            "estado",
        ]
        writer = csv.DictWriter(f, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["operaciones"])
    print(
        json.dumps(
            {**report["resumen"], "informe": str(base.with_suffix(".json"))},
            default=str,
            ensure_ascii=False,
        )
    )
