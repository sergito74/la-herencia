"""Vincular 59 VEP oficiales a 54 débitos: reparto documental, sin nuevos pagos.

--aplicar: respaldo verificado e invariantes. El cruce exige fecha/importe y
agrupación única; cada PDF fue validado contra CUIT, número e importe pagado.
"""
from decimal import Decimal as D
import json
from pathlib import Path
import sys

from src.db.connection import reconciliation_transaction, _reconciliation_connection
from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_corrientes import arca
from src.features.cuentas_corrientes.arca_documentos import verificar_archivo
from src.features.vinculos.backup import backup_verificado
from scripts.vincular_tres_pagos_condominio_036 import control

ROOT=Path(__file__).resolve().parents[2]/"backups/arca-continuacion-20261025"
REGLA="arca-veps-59-bancos-54-036"


def run(aplicar=False):
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'",(REGLA,)):
        return {"estado":"ya_aplicado_sin_escrituras"}
    plan=json.loads((ROOT/"veps-cruce-banco.json").read_text(encoding="utf-8"))
    if plan["noVinculados"] or plan["ambiguos"]:raise ValueError("Hay VEP sin cruce único")
    grupos=plan["grupos"]
    for g in grupos:
        b=g["banco"]
        if sum(D(v["total"]) for v in g["veps"])!=D(b["Débitos"]):raise ValueError("Suma diferente del banco")
        for v in g["veps"]:
            verificar_archivo(v["ruta"],v["sha256"])
            if v["fechaPago"]!=b["Fecha"][:10]:raise ValueError("Fecha de pago distinta")
    if not aplicar:return {"grupos":len(grupos),"PDF":sum(len(g["veps"]) for g in grupos)}
    respaldo=backup_verificado("arca-59-veps-036")
    cambios=[]
    with reconciliation_transaction():
        cur=_reconciliation_connection.get().cursor()
        antes=control(cur)
        for g in grupos:
            b=g["banco"];ident=b["IdMovimiento"]
            actual=read("SELECT * FROM dbo.[Movimientos Galicia] WITH (HOLDLOCK) WHERE IdMovimiento=?",(ident,))
            if json.loads(json.dumps(actual[0],default=str))!=b:raise ValueError("Cambió el movimiento bancario")
            importes={}
            for v in g["veps"]:importes[v["subcuenta"]]=importes.get(v["subcuenta"],D(0))+D(v["total"])
            partes=[{"subcuenta":s,"deuda":D(0),"credito":valor} for s,valor in importes.items()]
            m=read("SELECT TOP(1) IdClasificacion version,Reparto reparto,Motivo motivo FROM dbo.ArcaClasificaciones WHERE Origen='Galicia' AND IdOrigen=? ORDER BY IdClasificacion DESC",(ident,))
            if m and "F931 y VEP pagado oficial" not in m[0]["motivo"]:
                raise ValueError("Clasificación de otra procedencia: no sobrescribir")
            resultado=arca.guardar("Galicia",ident,m[0]["version"] if m else 0,partes,
                                  "VEP pagados oficiales ARCA "+", ".join(v["numero"] for v in g["veps"])+"; CUIT, fecha y suma exacta contra banco. Clasificación sin nuevos pagos.","Codex036")
            cambios.append({"galicia":ident,**resultado,"partes":partes})
            for v in g["veps"]:
                ya=read("SELECT 1 x FROM dbo.ArcaDocumentos WHERE Origen='Galicia' AND IdOrigen=? AND Numero=?",(ident,v["numero"]))
                if not ya:
                    cur.execute("INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario) VALUES ('Galicia',?,?,?,?,?,?,1,'Codex036')",
                                ident,"VEP pagado",v["periodo"],v["numero"],v["ruta"],v["sha256"])
        despues=control(cur)
        if antes!=despues:raise ValueError("Cambió un saldo contable con una clasificación")
        resultado={"backup":respaldo,"cambios":cambios,"movimientosBanco":54,"veps":59,"saldo":dict(antes["cuentas"])[119]}
        cur.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)",
                    REGLA,json.dumps(resultado,default=str,ensure_ascii=False),respaldo,"59 VEP pagados identificados en54débitos; PDF vinculados, F931/SICORE/Ganancias separados. Saldos, bancos, cajas y socios intactos.")
    (ROOT/"veps-clasificados.json").write_text(json.dumps(resultado,default=str,ensure_ascii=False,indent=2),encoding="utf-8")
    return {"estado":"aplicado","bancos":54,"veps":59,"saldoSinCambio":resultado["saldo"],"backup":respaldo}


if __name__=="__main__":print(json.dumps(run("--aplicar" in sys.argv),default=str,ensure_ascii=False,indent=2))
