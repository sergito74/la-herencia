"""Punto 4 (Autónomos Sergio y Lucy):
1. Corregir MovimientosCuentaSocio 2255 ($136.628,92 -> $160.290,79) y 2734 ($59.916,00 -> $56.016,36) con valuación 50/50 USD y kg carne.
2. Insertar las 48 obligaciones mensuales de Autónomos 09/2024..08/2026 (24 de Sergio por $2.930.369,56 y 24 de Lucy por $1.186.484,21) en dbo.Impuestos (IdOrganismo=119, IdTipoImpuesto=5) y vincular sus copias CCMA en dbo.ArcaDocumentos.
3. Vincular los 46 pagos existentes de socios en dbo.MovimientosCuentaSocio a IdContacto=119 en dbo.PagosSocioProveedor (sin duplicar 2160 que ya está).
4. Clasificar en dbo.ArcaClasificaciones las obligaciones nuevas y las 304 obligaciones históricas (152 Sergio + 152 Lucy), los pagos por socio de Lucy pagados desde la cuenta de Sergio, y los pagos en efectivo Particular S y Particular L.

Inspección por defecto. --aplicar: respaldo verificado, transacción, auditoría e invariantes.
"""
import argparse
from bisect import bisect_right
from collections import defaultdict
from datetime import date
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import _reconciliation_connection, reconciliation_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_corrientes import arca
from src.features.cuentas_corrientes.arca_documentos import RAIZ, verificar_archivo
from src.features.cuentas_socios.valuacion import calcular
from src.features.vinculos.backup import backup_verificado
from scripts.vincular_tres_pagos_condominio_036 import control

ROOT = Path(__file__).resolve().parents[2]
EVIDENCIA = ROOT / "backups/arca-continuacion-20261025"
REGLA = "arca-autonomos-ccma-socios-036"
USUARIO = "Gemini036"

OBLIGACIONES_SERGIO = [
    ("09 2024", "2024-10-09", D("84258.10")),
    ("10 2024", "2024-11-08", D("87771.66")),
    ("11 2024", "2024-12-09", D("90817.34")),
    ("12 2024", "2025-01-08", D("93260.33")),
    ("01 2025", "2025-02-07", D("95526.55")),
    ("02 2025", "2025-03-07", D("98105.78")),
    ("03 2025", "2025-04-09", D("100273.91")),
    ("04 2025", "2025-05-07", D("102680.48")),
    ("05 2025", "2025-06-09", D("106510.46")),
    ("06 2025", "2025-07-10", D("109471.45")),
    ("07 2025", "2025-08-07", D("111113.52")),
    ("08 2025", "2025-09-09", D("112913.56")),
    ("09 2025", "2025-10-08", D("115058.92")),
    ("10 2025", "2025-11-10", D("117222.02")),
    ("11 2025", "2025-12-10", D("119660.24")),
    ("12 2025", "2026-01-07", D("122460.30")),
    ("01 2026", "2026-02-09", D("125485.06")),
    ("02 2026", "2026-03-09", D("129061.38")),
    ("03 2026", "2026-04-08", D("132778.36")),
    ("04 2026", "2026-05-07", D("153985.59")),
    ("05 2026", "2026-06-09", D("141246.98")),
    ("06 2026", "2026-07-08", D("144891.15")),
    ("07 2026", "2026-08-07", D("148006.32")),
    ("08 2026", "2026-09-09", D("153985.59")),
]

OBLIGACIONES_LUCY = [
    ("09 2024", "2024-10-08", D("35546.70")),
    ("10 2024", "2024-11-07", D("37029.00")),
    ("11 2024", "2024-12-06", D("43318.70")),
    ("12 2024", "2025-01-07", D("39344.54")),
    ("01 2025", "2025-02-06", D("40300.62")),
    ("02 2025", "2025-03-06", D("41388.74")),
    ("03 2025", "2025-04-08", D("42303.42")),
    ("04 2025", "2025-05-06", D("43318.70")),
    ("05 2025", "2025-06-06", D("44934.49")),
    ("06 2025", "2025-07-08", D("46183.67")),
    ("07 2025", "2025-08-06", D("46876.42")),
    ("08 2025", "2025-09-08", D("47635.83")),
    ("09 2025", "2025-10-07", D("48540.90")),
    ("10 2025", "2025-11-07", D("49453.47")),
    ("11 2025", "2025-12-09", D("50482.10")),
    ("12 2025", "2026-01-06", D("51663.39")),
    ("01 2026", "2026-02-06", D("52939.47")),
    ("02 2026", "2026-03-06", D("54448.25")),
    ("03 2026", "2026-04-07", D("56016.36")),
    ("04 2026", "2026-05-06", D("57640.83")),
    ("05 2026", "2026-06-08", D("59589.10")),
    ("06 2026", "2026-07-07", D("61126.50")),
    ("07 2026", "2026-08-06", D("62440.71")),
    ("08 2026", "2026-09-08", D("63620.84")),
]

# Pagos de socios 09/2024..08/2026 que aún no están en PagosSocioProveedor:
# 22 pagos de Sergio (IdSocio=1) para Autónomos de Sergio:
PAGOS_SOCIO_SERGIO = [
    2145, 2148, 2150, 2153, 2157, 2165, 2172, 2176, 2182, 2186,
    2191, 2195, 2200, 2204, 2213, 2229, 2237, 2243, 2249, 2260,
    2266, 2275,
]
# 17 pagos de Lucy (IdSocio=2) para Autónomos de Lucy:
PAGOS_SOCIO_LUCY = [
    2661, 2667, 2672, 2680, 2681, 2690, 2694, 2702, 2708, 2711,
    2716, 2727, 2734, 2736, 2743, 2752, 2758, 2765,
]
# 7 pagos hechos desde la cuenta de Sergio (IdSocio=1) para Autónomos de Lucy (además de 2160 que ya está en PagosSocioProveedor):
PAGOS_SERGIO_POR_LUCY = [
    2166, 2180, 2196, 2205, 2214, 2228, 2236,
]


def dia(v):
    return date.fromisoformat(str(v)[:10])


def norm_per(p):
    parts = (p or "").strip().split()
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"{int(parts[0]):02d} {parts[1]}"
    return (p or "").strip()


def preparar_pdfs():
    archivos = [
        ("sergio", "CCMA-Sergio-202409-202609-copia.pdf"),
        ("lucy", "CCMA-Lucy-202409-202609-copia.pdf"),
    ]
    mapa = {}
    for clave, nombre in archivos:
        src = EVIDENCIA / nombre
        if not src.exists():
            raise ValueError(f"Falta PDF CCMA: {src}")
        sha = hashlib.sha256(src.read_bytes()).hexdigest()
        dst = RAIZ / "Autonomos" / nombre
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and hashlib.sha256(dst.read_bytes()).hexdigest() != sha:
            raise ValueError(f"Conflicto de hash en destino: {dst}")
        if not dst.exists():
            shutil.copy2(src, dst)
        verificar_archivo(dst, sha)
        mapa[clave] = {"nombre": nombre, "ruta": str(dst), "sha256": sha}
    return mapa


def planificar_clasificaciones_historicas():
    imp_aut = read("""
        SELECT IdImpuesto, CONVERT(varchar(10), Fecha, 23) fecha, [Periodo liquidado] periodo,
               [Numero de documento] nroDoc, Importe
        FROM dbo.Impuestos
        WHERE IdOrganismo = 119 AND IdTipoImpuesto = 5
        ORDER BY Fecha, IdImpuesto
    """)
    by_per = defaultdict(list)
    for r in imp_aut:
        by_per[norm_per(r["periodo"])].append(r)
    sergio_imp, lucy_imp = [], []
    for per, rows in sorted(by_per.items()):
        if len(rows) == 2:
            rs = sorted(rows, key=lambda x: D(str(x["Importe"])))
            lucy_imp.append(rs[0])
            sergio_imp.append(rs[1])
        elif per == "08 2020" and len(rows) == 1:
            lucy_imp.append(rows[0])

    sergio_amounts = {D(str(r["Importe"])) for r in sergio_imp}
    lucy_amounts = {D(str(r["Importe"])) for r in lucy_imp}

    pe_part = read("""
        SELECT IdPagoEfectivo, CONVERT(varchar(10), Fecha, 23) fecha, Cuenta, Caja,
               [Importe imputado] importe
        FROM dbo.vw_PagosEfectivoVigentes
        WHERE IdContacto = 119 AND Caja IN ('Particular S', 'Particular L')
        ORDER BY Fecha, IdPagoEfectivo
    """)
    pe_clasificar = []
    for p in pe_part:
        imp = D(str(p["importe"]))
        if p["Caja"] == "Particular S":
            if imp in sergio_amounts:
                sub = "autonomos-sergio"
                mot = "Pago en efectivo Particular S coincidente con obligación de Autónomos Sergio."
            elif imp in lucy_amounts:
                sub = "autonomos-lucy"
                mot = "Pago en efectivo Particular S (01/2024) coincidente con obligación de Autónomos Lucy."
            else:
                sub = "cargas-sociales"
                mot = "Pago en efectivo Particular S coincidente con Cargas Sociales servicio doméstico."
        else:
            if imp in lucy_amounts:
                sub = "autonomos-lucy"
                mot = "Pago en efectivo Particular L coincidente con obligación de Autónomos Lucy."
            else:
                sub = "cargas-sociales"
                mot = "Pago en efectivo Particular L coincidente con Cargas Sociales servicio doméstico."
        pe_clasificar.append({"idPagoEfectivo": p["IdPagoEfectivo"], "importe": imp, "subcuenta": sub, "motivo": mot})
    return sergio_imp, lucy_imp, pe_clasificar


def run(aplicar=False):
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (REGLA,)):
        return {"estado": "ya_aplicado_sin_escrituras"}
    pdfs = preparar_pdfs()
    dol = {dia(r["Fecha"]): r["Prom_billete"] for r in read("SELECT Fecha,Prom_billete FROM dbo.[Dolar BNA] WHERE Prom_billete>0 ORDER BY Fecha")}
    nov = {dia(r["Fecha"]): r["Indice"] for r in read("SELECT Fecha,Indice FROM dbo.IndiceINMAG ORDER BY Fecha")}

    def at(series, f):
        dias = sorted(series)
        i = bisect_right(dias, f) - 1
        return dias[i], series[dias[i]]

    ajustes_socio = {}
    for mid, nuevo_imp, detalle_ccma in (
        (2255, D("160290.79"), "CCMA 04/2026 pagado 05/10/2026 ($153.985,59 capital + $6.305,20 interés resarcitorio)"),
        (2734, D("56016.36"), "CCMA 03/2026 pagado 07/04/2026 ($56.016,36 obligación y pago oficial)"),
    ):
        r = read("SELECT * FROM dbo.MovimientosCuentaSocio WHERE IdMovimiento=?", (mid,))[0]
        f = dia(r["Fecha"])
        _, d = at(dol, f)
        _, n = at(nov, f)
        val = calcular(nuevo_imp, f, d, n)
        ajustes_socio[mid] = {
            "idMovimiento": mid,
            "idSocio": r["IdSocio"],
            "antesImporte": D(str(r["Importe"])),
            "antesUSD": D(str(r["ImporteUSD"])),
            "antesKg": D(str(r["ImporteKgCarne"])),
            "nuevoImporte": nuevo_imp,
            "nuevoUSD": val["importeUSD"],
            "nuevoKg": val["importeKgCarne"],
            "detalle": detalle_ccma,
        }

    sergio_imp_hist, lucy_imp_hist, pe_clasificar = planificar_clasificaciones_historicas()

    # Verificar los 47 movimientos de socio a vincular en PagosSocioProveedor
    todos_psp_nuevos = PAGOS_SOCIO_SERGIO + PAGOS_SOCIO_LUCY + PAGOS_SERGIO_POR_LUCY
    existentes_psp = {r["IdMovimientoSocio"] for r in read("SELECT IdMovimientoSocio FROM dbo.PagosSocioProveedor")}
    for mid in todos_psp_nuevos:
        if mid in existentes_psp:
            raise ValueError(f"El movimiento de socio {mid} ya está en PagosSocioProveedor")

    socios_rows = {
        r["IdMovimiento"]: r
        for r in read(
            f"SELECT IdMovimiento,IdSocio,Tipo,Importe,CONVERT(varchar(10),Fecha,23) fecha,Motivo,Anulada "
            f"FROM dbo.MovimientosCuentaSocio WHERE IdMovimiento IN ({','.join(str(x) for x in todos_psp_nuevos + [2160])})"
        )
    }
    if len(socios_rows) != len(todos_psp_nuevos) + 1:
        raise ValueError("Faltan filas en MovimientosCuentaSocio")

    total_obl_sergio = sum((x[2] for x in OBLIGACIONES_SERGIO), D(0))
    total_obl_lucy = sum((x[2] for x in OBLIGACIONES_LUCY), D(0))
    total_obl_nuevas = total_obl_sergio + total_obl_lucy

    # Calcular suma de créditos nuevos que entran a IdContacto=119 vía PagosSocioProveedor (con 2734 ya ajustado a 56016.36)
    total_psp_nuevos = sum(
        (ajustes_socio[mid]["nuevoImporte"] if mid in ajustes_socio else D(str(socios_rows[mid]["Importe"])))
        for mid in todos_psp_nuevos
    )

    plan = {
        "estado": "inspeccion",
        "ajustesSocio": ajustes_socio,
        "obligacionesNuevasSergio": len(OBLIGACIONES_SERGIO),
        "importeObligacionesSergio": total_obl_sergio,
        "obligacionesNuevasLucy": len(OBLIGACIONES_LUCY),
        "importeObligacionesLucy": total_obl_lucy,
        "totalObligacionesNuevas": total_obl_nuevas,
        "pagosSocioAVincular": len(todos_psp_nuevos),
        "importePagosSocioAVincular": total_psp_nuevos,
        "impuestosHistClasificar": len(sergio_imp_hist) + len(lucy_imp_hist),
        "pagosEfectivoClasificar": len(pe_clasificar),
    }
    (EVIDENCIA / "punto4-plan.json").write_text(json.dumps(plan, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    if not aplicar:
        return plan

    respaldo = backup_verificado("arca-autonomos-ccma-036")
    with reconciliation_transaction():
        cur = _reconciliation_connection.get().cursor()
        before = control(cur)

        # 1. Actualizar MovimientosCuentaSocio 2255 y 2734
        for mid, aj in ajustes_socio.items():
            cur.execute(
                "UPDATE dbo.MovimientosCuentaSocio SET Importe=?, ImporteUSD=?, ImporteKgCarne=? WHERE IdMovimiento=?",
                str(aj["nuevoImporte"]), str(aj["nuevoUSD"]), str(aj["nuevoKg"]), mid,
            )

        # 2. Insertar 48 obligaciones mensuales de Autónomos (09/2024..08/2026) en dbo.Impuestos
        insertadas = []
        for titular, lista, doc_key, subcuenta in (
            ("Sergio", OBLIGACIONES_SERGIO, "sergio", "autonomos-sergio"),
            ("Lucy", OBLIGACIONES_LUCY, "lucy", "autonomos-lucy"),
        ):
            doc = pdfs[doc_key]
            for per, fecha, imp in lista:
                cur.execute(
                    "INSERT INTO dbo.Impuestos (Fecha,IdOrganismo,IdTipoImpuesto,[Periodo liquidado],[Numero de documento],Importe,[Documento Original]) "
                    "OUTPUT INSERTED.IdImpuesto VALUES (?,119,5,?,?,?,?)",
                    fecha, per, f"CCMA {titular}", str(imp), doc["ruta"],
                )
                id_imp = cur.fetchone()[0]
                insertadas.append({"idImpuesto": id_imp, "titular": titular, "periodo": per, "fecha": fecha, "importe": imp})
                cur.execute(
                    "INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario) "
                    "VALUES ('Impuestos',?,'Estado de cuenta CCMA',?,?,?,?,0,?)",
                    id_imp, per.replace(" ", "/"), f"CCMA {titular}", doc["ruta"], doc["sha256"], USUARIO,
                )
                arca.guardar(
                    "Impuestos", id_imp, 0,
                    [{"subcuenta": subcuenta, "deuda": imp, "credito": D(0)}],
                    f"Obligación mensual Autónomos {titular} {per.replace(' ', '/')} según CCMA al corte 30/09/2026.",
                    USUARIO,
                )

        # 3. Vincular los 47 pagos existentes de socios en dbo.PagosSocioProveedor y sus copias CCMA
        for mid in PAGOS_SOCIO_SERGIO:
            cur.execute("INSERT INTO dbo.PagosSocioProveedor (IdMovimientoSocio,IdContacto,Criterio) VALUES (?,119,'ccma-036')", mid)
            doc = pdfs["sergio"]
            cur.execute(
                "INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario) "
                "VALUES ('Pago por socio',?,'Estado de cuenta CCMA',NULL,'CCMA Sergio',?,?,0,?)",
                mid, doc["ruta"], doc["sha256"], USUARIO,
            )
        for mid in PAGOS_SOCIO_LUCY:
            cur.execute("INSERT INTO dbo.PagosSocioProveedor (IdMovimientoSocio,IdContacto,Criterio) VALUES (?,119,'ccma-036')", mid)
            doc = pdfs["lucy"]
            cur.execute(
                "INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario) "
                "VALUES ('Pago por socio',?,'Estado de cuenta CCMA',NULL,'CCMA Lucy',?,?,0,?)",
                mid, doc["ruta"], doc["sha256"], USUARIO,
            )
        for mid in PAGOS_SERGIO_POR_LUCY:
            cur.execute("INSERT INTO dbo.PagosSocioProveedor (IdMovimientoSocio,IdContacto,Criterio) VALUES (?,119,'ccma-036')", mid)
            doc = pdfs["lucy"]
            cur.execute(
                "INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario) "
                "VALUES ('Pago por socio',?,'Estado de cuenta CCMA',NULL,'CCMA Lucy',?,?,0,?)",
                mid, doc["ruta"], doc["sha256"], USUARIO,
            )
            imp_m = D(str(socios_rows[mid]["Importe"]))
            arca.guardar(
                "Pago por socio", mid, 0,
                [{"subcuenta": "autonomos-lucy", "deuda": D(0), "credito": imp_m}],
                "Pago de Autónomos de Lucy realizado desde la cuenta de Sergio, confirmado en CCMA de Lucy.",
                USUARIO,
            )
        # También vincular el PDF CCMA de Lucy al pago 2160 ya existente en PagosSocioProveedor
        doc_l = pdfs["lucy"]
        if not read("SELECT 1 x FROM dbo.ArcaDocumentos WHERE Origen='Pago por socio' AND IdOrigen=2160"):
            cur.execute(
                "INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario) "
                "VALUES ('Pago por socio',2160,'Estado de cuenta CCMA','01/2025','CCMA Lucy',?,?,0,?)",
                doc_l["ruta"], doc_l["sha256"], USUARIO,
            )

        # 4. Clasificar las 304 obligaciones históricas de Autónomos (152 Sergio + 152 Lucy) y los 207 Pagos efectivo Particular S/L
        for r in sergio_imp_hist:
            imp = D(str(r["Importe"]))
            arca.guardar(
                "Impuestos", r["IdImpuesto"], 0,
                [{"subcuenta": "autonomos-sergio", "deuda": imp, "credito": D(0)}],
                f"Obligación histórica Autónomos Sergio ({norm_per(r['periodo'])}) identificada por par de categoría/pago del período.",
                USUARIO,
            )
        for r in lucy_imp_hist:
            imp = D(str(r["Importe"]))
            arca.guardar(
                "Impuestos", r["IdImpuesto"], 0,
                [{"subcuenta": "autonomos-lucy", "deuda": imp, "credito": D(0)}],
                f"Obligación histórica Autónomos Lucy ({norm_per(r['periodo'])}) identificada por par de categoría/pago del período.",
                USUARIO,
            )
        for p in pe_clasificar:
            arca.guardar(
                "Pagos efectivo", p["idPagoEfectivo"], 0,
                [{"subcuenta": p["subcuenta"], "deuda": D(0), "credito": p["importe"]}],
                p["motivo"],
                USUARIO,
            )

        after = control(cur)
        # Verificar invariantes exactos:
        # 1) Cajas no cambian
        if before["cajas"] != after["cajas"]:
            raise ValueError("Cambió una caja de efectivo")
        # 2) Cuenta 119 cambia exactamente en +total_psp_nuevos - total_obl_nuevas
        esperado_cuentas = dict(before["cuentas"])
        esperado_cuentas[119] = esperado_cuentas[119] + total_psp_nuevos - total_obl_nuevas
        if esperado_cuentas != dict(after["cuentas"]):
            raise ValueError(f"Cambio inesperado en cuentas: {esperado_cuentas[119]} vs {dict(after['cuentas'])[119]}")
        # 3) Socios cambian únicamente en socio 1 (asiento 2255) y socio 2 (asiento 2734)
        diff_s1 = ajustes_socio[2255]["nuevoImporte"] - ajustes_socio[2255]["antesImporte"]
        diff_s2 = ajustes_socio[2734]["nuevoImporte"] - ajustes_socio[2734]["antesImporte"]
        antes_soc = {r[0]: r for r in before["socios"]}
        desp_soc = {r[0]: r for r in after["socios"]}
        if D(str(desp_soc[1][2])) - D(str(antes_soc[1][2])) != diff_s1:
            raise ValueError(f"Cambio inesperado en socio 1: {desp_soc[1][2]} vs {antes_soc[1][2]}")
        if D(str(desp_soc[2][2])) - D(str(antes_soc[2][2])) != diff_s2:
            raise ValueError(f"Cambio inesperado en socio 2: {desp_soc[2][2]} vs {antes_soc[2][2]}")

        resultado = {
            "estado": "aplicado",
            "respaldo": respaldo,
            "ajustesSocio": ajustes_socio,
            "obligacionesInsertadas": len(insertadas),
            "totalObligacionesNuevas": total_obl_nuevas,
            "pagosSocioVinculados": len(todos_psp_nuevos),
            "totalPagosSocioVinculados": total_psp_nuevos,
            "impuestosHistClasificados": len(sergio_imp_hist) + len(lucy_imp_hist),
            "pagosEfectivoClasificados": len(pe_clasificar),
            "saldoAntes119": dict(before["cuentas"])[119],
            "saldoDespues119": dict(after["cuentas"])[119],
        }
        cur.execute(
            "INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
            "VALUES (?,'aplicada',?,?,SYSDATETIME(),?,SYSDATETIME(),?,?)",
            REGLA,
            json.dumps(resultado, default=str, ensure_ascii=False),
            USUARIO,
            USUARIO,
            respaldo,
            f"Autónomos CCMA: 48 obligaciones 09/2024..08/2026 por {total_obl_nuevas}; 47 pagos socio vinculados por {total_psp_nuevos}; asientos 2255 y 2734 ajustados a CCMA; 304 obligaciones históricas y 207 pagos Particular S/L clasificados.",
        )
    (EVIDENCIA / "punto4-aplicado.json").write_text(json.dumps(resultado, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=False, indent=2))

