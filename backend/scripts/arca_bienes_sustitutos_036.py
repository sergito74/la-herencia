"""Incorporar 15 obligaciones de planes Bienes Sustitutos (U657364 y W143471 al corte),
vincular los PDF de Mis Facilidades y clasificar las 32 cuotas Galicia de planes Q355709,
R586663 y T026731 en bienes-sustitutos.

Inspección por defecto. --aplicar: respaldo verificado, transacción, auditoría e invariantes.
"""
import argparse
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
from src.features.vinculos.backup import backup_verificado
from scripts.vincular_tres_pagos_condominio_036 import control

ROOT = Path(__file__).resolve().parents[2]
EVIDENCIA = ROOT / "backups/arca-analisis-20261025"
SALIDA = ROOT / "backups/arca-continuacion-20261025"
REGLA = "arca-bienes-sustitutos-planes-036"
USUARIO = "Gemini036"

CUOTAS_NUEVAS = [
    # Plan U657364 (Bienes Sustitutos 2024, 12 cuotas x $87.297,84 = $1.047.574,08)
    {"plan": "U657364", "periodo": "01 2024", "fecha": "2025-07-16", "importe": D("87297.84"), "galicia": 2675, "pdf": "Plan de Pagos 12 Cuotas - GIAMIGLI DE BOLIVAR SA.pdf"},
    {"plan": "U657364", "periodo": "02 2024", "fecha": "2025-08-16", "importe": D("87297.84"), "galicia": 2738, "pdf": "Plan de Pagos 12 Cuotas - GIAMIGLI DE BOLIVAR SA.pdf"},
    {"plan": "U657364", "periodo": "03 2024", "fecha": "2025-09-16", "importe": D("87297.84"), "galicia": 2787, "pdf": "Plan de Pagos 12 Cuotas - GIAMIGLI DE BOLIVAR SA.pdf"},
    {"plan": "U657364", "periodo": "04 2024", "fecha": "2025-10-16", "importe": D("87297.84"), "galicia": 2835, "pdf": "Plan de Pagos 12 Cuotas - GIAMIGLI DE BOLIVAR SA.pdf"},
    {"plan": "U657364", "periodo": "05 2024", "fecha": "2025-11-16", "importe": D("87297.84"), "galicia": 2893, "pdf": "Plan de Pagos 12 Cuotas - GIAMIGLI DE BOLIVAR SA.pdf"},
    {"plan": "U657364", "periodo": "06 2024", "fecha": "2025-12-16", "importe": D("87297.84"), "galicia": 2954, "pdf": "Plan de Pagos 12 Cuotas - GIAMIGLI DE BOLIVAR SA.pdf"},
    {"plan": "U657364", "periodo": "07 2024", "fecha": "2026-01-16", "importe": D("87297.84"), "galicia": 3008, "pdf": "Plan de Pagos 12 Cuotas - GIAMIGLI DE BOLIVAR SA.pdf"},
    {"plan": "U657364", "periodo": "08 2024", "fecha": "2026-02-16", "importe": D("87297.84"), "galicia": 3057, "pdf": "Plan de Pagos 12 Cuotas - GIAMIGLI DE BOLIVAR SA.pdf"},
    {"plan": "U657364", "periodo": "09 2024", "fecha": "2026-03-16", "importe": D("87297.84"), "galicia": 3104, "pdf": "Plan de Pagos 12 Cuotas - GIAMIGLI DE BOLIVAR SA.pdf"},
    {"plan": "U657364", "periodo": "10 2024", "fecha": "2026-04-16", "importe": D("87297.84"), "galicia": 3159, "pdf": "Plan de Pagos 12 Cuotas - GIAMIGLI DE BOLIVAR SA.pdf"},
    {"plan": "U657364", "periodo": "11 2024", "fecha": "2026-05-16", "importe": D("87297.84"), "galicia": 3220, "pdf": "Plan de Pagos 12 Cuotas - GIAMIGLI DE BOLIVAR SA.pdf"},
    {"plan": "U657364", "periodo": "12 2024", "fecha": "2026-06-16", "importe": D("87297.84"), "galicia": 3276, "pdf": "Plan de Pagos 12 Cuotas - GIAMIGLI DE BOLIVAR SA.pdf"},
    # Plan W143471 (Bienes Sustitutos 2025, 3 cuotas al corte 30/09/2026 x $126.660,54 = $379.981,62)
    {"plan": "W143471", "periodo": "01 2025", "fecha": "2026-07-16", "importe": D("126660.54"), "galicia": 3329, "pdf": "Plan de Pagos Bs Sustituto 2025 - GIAMIGLI DE BOLIVAR SA.pdf"},
    {"plan": "W143471", "periodo": "02 2025", "fecha": "2026-08-16", "importe": D("126660.54"), "galicia": 3384, "pdf": "Plan de Pagos Bs Sustituto 2025 - GIAMIGLI DE BOLIVAR SA.pdf"},
    {"plan": "W143471", "periodo": "03 2025", "fecha": "2026-09-16", "importe": D("126660.54"), "galicia": 3451, "pdf": "Plan de Pagos Bs Sustituto 2025 - GIAMIGLI DE BOLIVAR SA.pdf"},
]

PAGOS_CLASIFICAR = [
    # Plan Q355709 (8 cuotas x $15.483,08)
    *(
        {"plan": "Q355709", "ejercicio": 2021, "importe": D("15483.08"), "galicia": gid}
        for gid in (653, 712, 761, 814, 857, 908, 975, 1034)
    ),
    # Plan R586663 (12 cuotas x $25.630,61)
    *(
        {"plan": "R586663", "ejercicio": 2022, "importe": D("25630.61"), "galicia": gid, "pdf": "Plan de Pagos - Bs Sustituto 2022 - Giamigli de Bolivar SA.pdf"}
        for gid in (1264, 1309, 1369, 1418, 1472, 1560, 1596, 1669, 1733, 1786, 1828, 1890)
    ),
    # Plan T026731 (12 cuotas x $40.250,95)
    *(
        {"plan": "T026731", "ejercicio": 2023, "importe": D("40250.95"), "galicia": gid}
        for gid in (2009, 2061, 2101, 2166, 2221, 2270, 2339, 2402, 2462, 2517, 2558, 2619)
    ),
]


def preparar_pdfs():
    nombres = {
        "Plan de Pagos - Bs Sustituto 2022 - Giamigli de Bolivar SA.pdf",
        "Plan de Pagos 12 Cuotas - GIAMIGLI DE BOLIVAR SA.pdf",
        "Plan de Pagos Bs Sustituto 2025 - GIAMIGLI DE BOLIVAR SA.pdf",
    }
    mapa = {}
    for nombre in sorted(nombres):
        src = EVIDENCIA / nombre
        if not src.exists():
            raise ValueError(f"Falta PDF fuente: {src}")
        sha = hashlib.sha256(src.read_bytes()).hexdigest()
        dst = RAIZ / "Bienes Sustitutos" / nombre
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and hashlib.sha256(dst.read_bytes()).hexdigest() != sha:
            raise ValueError(f"Conflicto de hash en destino: {dst}")
        if not dst.exists():
            shutil.copy2(src, dst)
        verificar_archivo(dst, sha)
        mapa[nombre] = {"nombre": nombre, "ruta": str(dst), "sha256": sha}
    return mapa


def run(aplicar=False):
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (REGLA,)):
        return {"estado": "ya_aplicado_sin_escrituras"}
    pdfs = preparar_pdfs()
    impuestos = read("SELECT * FROM dbo.Impuestos WHERE IdOrganismo=119 AND IdTipoImpuesto=13 ORDER BY IdImpuesto")
    for c in CUOTAS_NUEVAS:
        if any((i["Numero de documento"] or "").strip() == c["plan"] and (i["Periodo liquidado"] or "").strip() == c["periodo"] for i in impuestos):
            raise ValueError(f"Ya existe obligación {c['plan']} {c['periodo']}")
        b = read("SELECT IdMovimiento,Fecha,[Débitos] debito,[Créditos] credito,IdContacto FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=?", (c["galicia"],))
        if len(b) != 1 or b[0]["IdContacto"] != 119 or D(str(b[0]["debito"])) != c["importe"] or b[0]["credito"]:
            raise ValueError(f"No coincide débito Galicia {c['galicia']} con cuota {c['plan']}")
    for p in PAGOS_CLASIFICAR:
        b = read("SELECT IdMovimiento,Fecha,[Débitos] debito,[Créditos] credito,IdContacto FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=?", (p["galicia"],))
        if len(b) != 1 or b[0]["IdContacto"] != 119 or D(str(b[0]["debito"])) != p["importe"] or b[0]["credito"]:
            raise ValueError(f"No coincide débito Galicia {p['galicia']} con plan {p['plan']}")
        actual = read("SELECT TOP(1) IdClasificacion version FROM dbo.ArcaClasificaciones WHERE Origen='Galicia' AND IdOrigen=? ORDER BY IdClasificacion DESC", (p["galicia"],))
        if actual:
            raise ValueError(f"Ya existe clasificación en Galicia {p['galicia']}")
    total_nuevas = sum((c["importe"] for c in CUOTAS_NUEVAS), D(0))
    total_clasificar = sum((p["importe"] for p in PAGOS_CLASIFICAR), D(0))
    resumen_plan = {
        "estado": "inspeccion",
        "obligacionesNuevas": len(CUOTAS_NUEVAS),
        "importeObligacionesNuevas": total_nuevas,
        "pagosAClasificar": len(PAGOS_CLASIFICAR),
        "importePagosAClasificar": total_clasificar,
        "pdfs": pdfs,
    }
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "punto5-plan.json").write_text(json.dumps(resumen_plan, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    if not aplicar:
        return resumen_plan

    respaldo = backup_verificado("arca-bienes-sustitutos-036")
    insertadas = []
    clasificadas = []
    with reconciliation_transaction():
        cur = _reconciliation_connection.get().cursor()
        before = control(cur)
        if read("SELECT * FROM dbo.Impuestos WHERE IdOrganismo=119 AND IdTipoImpuesto=13 ORDER BY IdImpuesto") != impuestos:
            raise ValueError("Cambió el inventario de Bienes Sustitutos")
        # 1. Insertar las 15 obligaciones de U657364 y W143471 y vincular sus PDF
        for c in CUOTAS_NUEVAS:
            doc = pdfs[c["pdf"]]
            cur.execute(
                "INSERT INTO dbo.Impuestos (Fecha,IdOrganismo,IdTipoImpuesto,[Periodo liquidado],[Numero de documento],Importe,[Documento Original]) "
                "OUTPUT INSERTED.IdImpuesto VALUES (?,119,13,?,?,?,?)",
                c["fecha"], c["periodo"], c["plan"], str(c["importe"]), doc["ruta"],
            )
            id_imp = cur.fetchone()[0]
            insertadas.append({"idImpuesto": id_imp, **c})
            for origen, ident in (("Impuestos", id_imp), ("Galicia", c["galicia"])):
                ya = read("SELECT 1 x FROM dbo.ArcaDocumentos WHERE Origen=? AND IdOrigen=? AND Ruta=?", (origen, ident, doc["ruta"]))
                if not ya:
                    cur.execute(
                        "INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario) "
                        "VALUES (?,?,?,?,?,?,?,1,?)",
                        origen, ident, "Plan Mis Facilidades RG 5321", c["periodo"].replace(" ", "/"), c["plan"], doc["ruta"], doc["sha256"], USUARIO,
                    )
        # 2. Vincular el PDF de R586663 a las 12 obligaciones existentes (IdImpuesto 862..873)
        doc_r = pdfs["Plan de Pagos - Bs Sustituto 2022 - Giamigli de Bolivar SA.pdf"]
        for i in impuestos:
            if (i["Numero de documento"] or "").strip() == "R586663":
                ya = read("SELECT 1 x FROM dbo.ArcaDocumentos WHERE Origen='Impuestos' AND IdOrigen=? AND Ruta=?", (i["IdImpuesto"], doc_r["ruta"]))
                if not ya:
                    cur.execute(
                        "INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario) "
                        "VALUES ('Impuestos',?,'Plan Mis Facilidades RG 5321',?,'R586663',?,?,1,?)",
                        i["IdImpuesto"], (i["Periodo liquidado"] or "").strip().replace(" ", "/"), doc_r["ruta"], doc_r["sha256"], USUARIO,
                    )
        # 3. Clasificar los 32 débitos Galicia de Q355709, R586663 y T026731 en bienes-sustitutos
        for p in PAGOS_CLASIFICAR:
            partes = [{"subcuenta": "bienes-sustitutos", "deuda": D(0), "credito": p["importe"]}]
            motivo = f"Plan {p['plan']}, Bienes Sustitutos {p['ejercicio']}: cuota pagada confirmada en Mis Facilidades y débito Galicia. Solo clasificación."
            res_c = arca.guardar("Galicia", p["galicia"], 0, partes, motivo, USUARIO)
            clasificadas.append({"galicia": p["galicia"], "plan": p["plan"], "importe": p["importe"], **res_c})
            if "pdf" in p:
                doc = pdfs[p["pdf"]]
                ya = read("SELECT 1 x FROM dbo.ArcaDocumentos WHERE Origen='Galicia' AND IdOrigen=? AND Ruta=?", (p["galicia"], doc["ruta"]))
                if not ya:
                    cur.execute(
                        "INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario) "
                        "VALUES ('Galicia',?,'Plan Mis Facilidades RG 5321',?,?,?,?,1,?)",
                        p["galicia"], str(p["ejercicio"]), p["plan"], doc["ruta"], doc["sha256"], USUARIO,
                    )
        after = control(cur)
        esperado = dict(before["cuentas"])
        esperado[119] -= total_nuevas
        if esperado != dict(after["cuentas"]) or before["cajas"] != after["cajas"] or before["socios"] != after["socios"]:
            raise ValueError("Cambió una cuenta, caja o socio fuera de lo previsto")
        resultado = {
            "estado": "aplicado",
            "respaldo": respaldo,
            "obligacionesInsertadas": insertadas,
            "totalObligacionesNuevas": total_nuevas,
            "pagosClasificados": clasificadas,
            "totalPagosClasificados": total_clasificar,
            "saldoAntes": dict(before["cuentas"])[119],
            "saldoDespues": dict(after["cuentas"])[119],
        }
        cur.execute(
            "INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
            "VALUES (?,'aplicada',?,?,SYSDATETIME(),?,SYSDATETIME(),?,?)",
            REGLA,
            json.dumps(resultado, default=str, ensure_ascii=False),
            USUARIO,
            USUARIO,
            respaldo,
            f"15 cuotas Bienes Sustitutos (U657364 12x87.297,84 y W143471 3x126.660,54 al corte) por {total_nuevas}; 32 débitos Galicia (Q355709, R586663, T026731) clasificados en bienes-sustitutos por {total_clasificar}. Sin pagos nuevos ni cambios a cajas/socios.",
        )
    (SALIDA / "punto5-aplicado.json").write_text(json.dumps(resultado, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "estado": "aplicado",
        "obligacionesNuevas": len(insertadas),
        "importeNuevas": total_nuevas,
        "pagosClasificados": len(clasificadas),
        "importeClasificados": total_clasificar,
        "saldoAntes": resultado["saldoAntes"],
        "saldoDespues": resultado["saldoDespues"],
        "respaldo": respaldo,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=False, indent=2))
