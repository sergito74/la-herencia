"""036: obligaciones F931 documentadas; opciones para PDFs locales de 2025.

Inspección por defecto; --aplicar: backup verificado, transacción única,
auditoría, invariantes y repetición sin escrituras. No crea pagos ni asientos
de socios, no cierra AFIP ni ejecuta FIFO sobre sus obligaciones incompletas.
"""
import argparse
import hashlib
import json
import shutil
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path

from src.db.connection import _assert_target_is_wc, _reconciliation_connection, reconciliation_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.vinculos.backup import backup_verificado
from scripts.vincular_tres_pagos_condominio_036 import control

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "backups/afip-f931-20261025"
RULE = "afip-f931-junio-agosto-2026-036"
PLAN = [
    {"periodo": "06 2026", "fecha": "2026-07-10", "vencimiento": "2026-07-13", "importe": D("1655802.40"),
     "numero": "VEP 1651061700", "galicia": 3321, "pago": "2026-07-13", "archivo": "F931 DDJJ JUN26.pdf"},
    {"periodo": "07 2026", "fecha": "2026-08-06", "vencimiento": "2026-08-10", "importe": D("1033322.13"),
     "numero": "VEP 1663700530", "galicia": 3372, "pago": "2026-08-10", "archivo": "F931 VEP JUL26.pdf"},
    {"periodo": "08 2026", "fecha": "2026-09-07", "vencimiento": "2026-09-09", "importe": D("1036592.72"),
     "numero": "VEP 1677451992", "galicia": 3439, "pago": "2026-09-08", "archivo": "F931 VEP AGO26.pdf"},
]
LOCALES_2025 = [
    {"periodo": "10 2025", "fecha": "2025-11-05", "criterioFecha": "Fecha contable del pago; PDF sin fecha de emisión impresa",
     "importe": D("878919.65"), "numero": "VEP 1540866121", "galicia": 2869, "pago": "2025-11-05", "archivo": "F931 10 2025.pdf",
     "visual": True, "hashOriginal": "fab34b68fbeecf2badfad1839268909c56f877966993f6339e1da0b9b77c4a07",
     "componentes": ["269494.80", "198651.91", "20106.17", "69302.35", "20106.17", "34651.17", "266272.40", "334.68"]},
    {"periodo": "11 2025", "fecha": "2025-12-09", "criterioFecha": "Fecha contable del pago; PDF sin fecha de emisión impresa",
     "importe": D("952657.06"), "numero": "VEP 1553619192", "galicia": 2931, "pago": "2025-12-09", "archivo": "F931 11 2025.pdf",
     "visual": True, "hashOriginal": "3ed52bc2e3eda66260c08da43e06fd98425ebf78ac2ea712844519b22b9e98b2",
     "componentes": ["296762.74", "219487.05", "21899.42", "74511.87", "21899.42", "37255.93", "280505.95", "334.68"]},
]
DICIEMBRE_2025 = [{
    "periodo": "12 2025", "fecha": "2026-01-07", "criterioFecha": "Fecha del aviso del estudio corroborado; PDF sin fecha impresa",
    "importe": D("1311952.66"), "numero": "F931 12/2025 - 340707", "galicia": 2991, "pago": "2026-01-09",
    "importePago": D("1548334.45"), "pagoEsCandidato": True, "pendienteConciliarPago": D("236381.79"),
    "archivo": "F931 12 2025.pdf", "visual": True,
    "hashOriginal": "d87462f875d0b9274c9e9531421202f0d446341fbcdfb43720668283d68b23b7",
    "componentes": ["403507.19", "297153.63", "29951.65", "102986.15", "29951.65", "51493.08", "396562.63", "346.68"],
}]


def dump(path, data):
    path.write_text(json.dumps(data, default=str, ensure_ascii=False, indent=2), encoding="utf-8")


def run(aplicar=False):
    _assert_target_is_wc()
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        return {"estado": "ya_aplicado_sin_escrituras"}
    manifests = json.loads((FOLDER / "mails.json").read_text(encoding="utf-8-sig"))
    hashes = {Path(f["File"]).name: f["Sha256"].lower() for m in manifests for f in m["Files"]}
    textos = json.loads((FOLDER / "textos.json").read_text(encoding="utf-8"))
    for p in PLAN:
        archivo = FOLDER / p["archivo"]
        if p.get("pagoEsCandidato"):
            aviso = json.loads((FOLDER / "aviso-diciembre2025.json").read_text(encoding="utf-8-sig"))
            if "1.311.952,66" not in aviso["Body"] or "12/2025" not in aviso["Subject"]:
                raise ValueError("El aviso del estudio no confirma diciembre")
            p["avisoEstudio"] = {k: aviso[k] for k in ("Subject", "Date", "EntryID")}
        if p.get("visual"):
            origen = Path("C:/Users/Sergio/Documents/La Herencia/Administracion y gestion/Personal/F 931") / p["archivo"]
            if hashlib.sha256(origen.read_bytes()).hexdigest() != p["hashOriginal"]:
                raise ValueError("Cambió el PDF revisado visualmente")
            if sum(D(c) for c in p["componentes"]) != p["importe"]:
                raise ValueError("La suma visual del cuadro VIII no coincide")
            if not archivo.exists():
                shutil.copy2(origen, archivo)
            hash_ = p["hashOriginal"]
        else:
            text = textos[p["archivo"]]
            periodo = p["periodo"][3:] + "-" + p["periodo"][:2]
            if "30-71211460-2" not in text or (periodo not in text and p["periodo"][:2] + "/" + p["periodo"][3:] not in text):
                raise ValueError("Documento de otra empresa o período")
            if "VEP" in p["archivo"] and p["numero"].split()[-1] not in text:
                raise ValueError("Número VEP no corroborado")
            hash_ = hashes[p["archivo"]]
        if hashlib.sha256(archivo.read_bytes()).hexdigest() != hash_:
            raise ValueError("Cambió un PDF fuente")
        p["sha256"] = hash_
        bank = read("SELECT IdMovimiento,Fecha,IdContacto,[Débitos],[Créditos],LeyendasAdicionales2 FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=?", (p["galicia"],))
        if len(bank) != 1 or bank[0]["IdContacto"] != 119 or bank[0]["Débitos"] != p.get("importePago", p["importe"]) or str(bank[0]["Fecha"])[:10] != p["pago"]:
            raise ValueError("Débito Galicia diferente del cotejado")
        p["bancoAntes"] = bank[0]
    impuestos = read("SELECT * FROM dbo.Impuestos WHERE IdOrganismo=119 ORDER BY IdImpuesto")
    # Bloquea variantes de formato del período y del número, no solo la misma clave textual.
    for r in impuestos:
        periodo = (r["Periodo liquidado"] or "").replace("/", " ").replace("-", " ")
        if any(periodo == p["periodo"] and r["IdTipoImpuesto"] == 2 or r["Numero de documento"] == p["numero"] for p in PLAN):
            raise ValueError("Ya existe una obligación candidata; revisar sin duplicar")
    result = {"estado": "inspeccion", "plan": PLAN, "importe": sum(p["importe"] for p in PLAN)}
    dump(FOLDER / (RULE + "-plan.json"), result)
    if not aplicar:
        return {"estado": "inspeccion", "obligaciones": len(PLAN), "importe": result["importe"]}
    backup = backup_verificado("afip_f931_junio_agosto_2026_036")
    snapshot = FOLDER / f"aplicacion-{datetime.now():%Y%m%d-%H%M%S}.json"
    result.update(respaldo=backup, impuestosAntes=impuestos)
    dump(snapshot, result)
    with reconciliation_transaction():
        c = _reconciliation_connection.get().cursor()
        c.execute("SELECT * FROM dbo.Impuestos WITH (UPDLOCK,HOLDLOCK) WHERE IdOrganismo=119 ORDER BY IdImpuesto")
        names = [d[0] for d in c.description]
        if [dict(zip(names, row, strict=True)) for row in c.fetchall()] != impuestos:
            raise ValueError("Cambiaron las obligaciones desde la inspección")
        before = control(c)
        for p in PLAN:
            c.execute("SELECT IdMovimiento,Fecha,IdContacto,[Débitos],[Créditos],LeyendasAdicionales2 FROM dbo.[Movimientos Galicia] WITH (HOLDLOCK) WHERE IdMovimiento=?", p["galicia"])
            names = [d[0] for d in c.description]
            if dict(zip(names, c.fetchone(), strict=True)) != p["bancoAntes"]:
                raise ValueError("Cambió el pago antes de registrar la obligación")
            c.execute("INSERT INTO dbo.Impuestos (Fecha,IdOrganismo,IdTipoImpuesto,[Periodo liquidado],[Numero de documento],Importe,[Documento Original]) "
                      "OUTPUT INSERTED.IdImpuesto VALUES (?,119,2,?,?,?,?)",
                      p["fecha"], p["periodo"], p["numero"], str(p["importe"]), str(FOLDER / p["archivo"]))
            p["idImpuesto"] = c.fetchone()[0]
        after = control(c)
        expected = {id_: importe for id_, importe in before["cuentas"]}
        expected[119] -= result["importe"]
        if expected != {id_: importe for id_, importe in after["cuentas"]}:
            raise ValueError("Variación de cuentas distinta de las tres obligaciones")
        if before["cajas"] != after["cajas"] or before["socios"] != after["socios"]:
            raise ValueError("Cambió una caja o un socio")
        c.execute("SELECT COUNT(*) FROM dbo.Impuestos WHERE IdOrganismo=119")
        if c.fetchone()[0] != len(impuestos) + len(PLAN):
            raise ValueError("Cantidad de impuestos inesperada")
        result.update(estado="aplicado", saldoAntes=dict(before["cuentas"])[119], saldoDespues=dict(after["cuentas"])[119], snapshot=str(snapshot))
        c.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)",
                  RULE, json.dumps(result, default=str, ensure_ascii=False), backup,
                  f"AFIP119: {len(PLAN)} obligaciones F931 por {result['importe']}; pagos preservados. Carga parcial, no cierre ni crédito fiscal confirmado.")
    dump(snapshot, result)
    return {k: v for k, v in result.items() if k not in ("impuestosAntes", "plan")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("--locales-2025", action="store_true", help="F931 octubre/noviembre2025 revisados visualmente y cotejados con Galicia")
    parser.add_argument("--diciembre-2025", action="store_true", help="Obligación confirmada por PDF y aviso; pago2991 candidato con diferencia, no imputado automáticamente")
    args = parser.parse_args()
    if args.locales_2025 and args.diciembre_2025:
        parser.error("Elegir un único lote")
    if args.locales_2025:
        PLAN = LOCALES_2025
        RULE = "afip-f931-octubre-noviembre-2025-036"
    if args.diciembre_2025:
        PLAN = DICIEMBRE_2025
        RULE = "afip-f931-diciembre-2025-036"
    print(json.dumps(run(args.aplicar), default=str, ensure_ascii=False, indent=2))
