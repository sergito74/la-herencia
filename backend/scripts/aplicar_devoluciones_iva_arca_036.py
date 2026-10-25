"""Aplicar 26 devoluciones de certificados contra9reintegros oficiales RE-Granos.

--aplicar requiere respaldo e invariantes; no crea otro cobro bancario.
"""
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import shutil
import sys

from src.db.connection import reconciliation_transaction, _reconciliation_connection
from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_corrientes.arca_documentos import RAIZ, verificar_archivo
from src.features.vinculos.backup import backup_verificado
from scripts.vincular_tres_pagos_condominio_036 import control

ROOT=Path(__file__).resolve().parents[2]
EVID=ROOT/"backups/arca-continuacion-20261025"
REGLA="arca-iva-26-devoluciones-regranos-036"


def dinero(s):return D(str(s).replace(".","").replace(",","."))


def run(aplicar=False):
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'",(REGLA,)):
        return {"estado":"ya_aplicado_sin_escrituras"}
    propuestas=json.loads((ROOT/"backups/arca-analisis-20261025/analisis.json").read_text(encoding="utf-8"))["reintegrosIdentificadosPropuestos"]
    pagos=json.loads((EVID/"devoluciones-portal.json").read_text(encoding="utf-8"))
    detalles=json.loads((EVID/"devoluciones-detalles.json").read_text(encoding="utf-8"))
    plan=[]
    for g in propuestas:
        candidatos=[p for p in pagos if dinero(p[10])==D(g["importe"]) and p[5]=="Pagado"]
        if len(candidatos)!=1:raise ValueError("Reintegro sin comprobación única en ARCA")
        pago=candidatos[0]
        detalle=next(d for d in detalles if d["sap"]==pago[4])
        if sum(dinero(d[9]) for d in detalle["detalle"])!=D(g["importe"]) or any(d[0]!="RE-Granos" for d in detalle["detalle"]):
            raise ValueError("El organismo no confirma RE-Granos por el importe esperado")
        original=EVID/detalle["archivo"]
        if hashlib.sha256(original.read_bytes()).hexdigest()!=detalle["sha256"]:raise ValueError("Cambió el PDF oficial")
        destino=RAIZ/"IVA/Devoluciones"/original.name
        destino.parent.mkdir(exist_ok=True,parents=True)
        if destino.exists() and hashlib.sha256(destino.read_bytes()).hexdigest()!=detalle["sha256"]:raise ValueError("Otra copia existente")
        if not destino.exists():shutil.copy2(original,destino)
        verificar_archivo(destino,detalle["sha256"])
        ids=[c["IdRetencion"] for c in g["certificados"]]
        actuales=[]
        for ident in ids:
            c=read("SELECT * FROM dbo.[Retenciones IVA Granos] WHERE IdRetencion=?",(ident,))[0]
            if c["Importe Devolucion"]!=0:raise ValueError("Certificado con devolución previa; no repetir")
            actuales.append(c)
        if sum(c["Importe Retenido"] for c in actuales)!=D(g["importe"]):raise ValueError("La retención cambió")
        banco=read("SELECT IdMovimiento,Fecha,[Créditos] credito,IdContacto FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=?",(g["galicia"],))[0]
        if banco["IdContacto"]!=119 or banco["credito"]!=D(g["importe"]):raise ValueError("Abono bancario distinto")
        plan.append({"galicia":g["galicia"],"banco":banco,"pagoARCA":pago,"certificadosAntes":actuales,
                     "ruta":str(destino),"sha256":detalle["sha256"],"importe":D(g["importe"])})
    total=sum(p["importe"] for p in plan)
    if not aplicar:return {"estado":"inspeccion","reintegros":len(plan),"certificados":sum(len(p["certificadosAntes"]) for p in plan),"importe":total}
    backup=backup_verificado("arca-iva-devoluciones-036")
    with reconciliation_transaction():
        cur=_reconciliation_connection.get().cursor()
        antes=control(cur)
        for p in plan:
            b=read("SELECT IdMovimiento,Fecha,[Créditos] credito,IdContacto FROM dbo.[Movimientos Galicia] WITH(HOLDLOCK) WHERE IdMovimiento=?",(p["galicia"],))
            if b!=[p["banco"]]:raise ValueError("Cambió el banco antes de confirmar")
            claves=[("Galicia",p["galicia"])]
            for c in p["certificadosAntes"]:
                actual=read("SELECT * FROM dbo.[Retenciones IVA Granos] WITH(UPDLOCK,HOLDLOCK) WHERE IdRetencion=?",(c["IdRetencion"],))
                if actual!=[c]:raise ValueError("Cambió el certificado")
                cur.execute("UPDATE dbo.[Retenciones IVA Granos] SET [Importe Devolucion]=[Importe Retenido] WHERE IdRetencion=?",c["IdRetencion"])
                # IdOrigen del mayor es IdLiquidacion, no IdRetencion.
                claves.append(("Ret. IVA Granos",c["IdLiquidacion"]))
            for origen,ident in claves:
                cur.execute("INSERT INTO dbo.ArcaDocumentos(Origen,IdOrigen,Tipo,Numero,Ruta,Sha256,EsOriginal,Usuario) VALUES (?,?,?,?,?,?,1,'Codex036')",
                            origen,ident,"Reintegro RE-Granos — pago ARCA",p["pagoARCA"][4],p["ruta"],p["sha256"])
        despues=control(cur)
        esperado=dict(antes["cuentas"]);esperado[119]+=total
        if esperado!=dict(despues["cuentas"]) or antes["cajas"]!=despues["cajas"] or antes["socios"]!=despues["socios"]:
            raise ValueError("Variación diferente de las devoluciones previstas")
        resultado={"backup":backup,"plan":plan,"importe":total,"saldoAntes":dict(antes["cuentas"])[119],"saldoDespues":dict(despues["cuentas"])[119]}
        cur.execute("INSERT INTO dbo.AuditoriaCorrecciones(Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)",
                    REGLA,json.dumps(resultado,default=str,ensure_ascii=False),backup,"26certificados vinculados a9reintegros RE-Granos oficiales por13.179.515,62; sin nuevos movimientos de banco/caja/socios.")
    (EVID/"iva-devoluciones-aplicadas.json").write_text(json.dumps(resultado,default=str,ensure_ascii=False,indent=2),encoding="utf-8")
    return {"estado":"aplicado","importe":total,"saldo":resultado["saldoDespues"],"backup":backup}


def reparar_vinculos():
    regla="arca-iva-documentos-idliquidacion-036"
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'",(regla,)):
        return {"estado":"ya_aplicado_sin_escrituras"}
    # Solo los enlaces inválidos creados por esta aplicación, contrastados con
    # su snapshot; no convertir claves por coincidencia de número.
    aplicado=json.loads((EVID/"iva-devoluciones-aplicadas.json").read_text(encoding="utf-8"))
    cambios=[]
    for p in aplicado["plan"]:
        for c in p["certificadosAntes"]:
            rows=read("SELECT IdDocumento,IdOrigen FROM dbo.ArcaDocumentos WHERE Origen='Ret. IVA Granos' AND IdOrigen=? AND Numero=? AND Sha256=?",(c["IdRetencion"],p["pagoARCA"][4],p["sha256"]))
            if len(rows)!=1:raise ValueError("El enlace no coincide con el snapshot")
            origen=read("SELECT IdOrigen FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=119 AND Origen='Ret. IVA Granos' AND IdOrigen=?",(c["IdLiquidacion"],))
            if len(origen)!=1:raise ValueError("No existe la liquidación esperada")
            cambios.append({"idDocumento":rows[0]["IdDocumento"],"antes":c["IdRetencion"],"despues":c["IdLiquidacion"]})
    backup=backup_verificado("arca-iva-enlaces-036")
    with reconciliation_transaction():
        cur=_reconciliation_connection.get().cursor()
        before=control(cur)
        for c in cambios:
            cur.execute("UPDATE dbo.ArcaDocumentos SET IdOrigen=? WHERE IdDocumento=? AND IdOrigen=?",c["despues"],c["idDocumento"],c["antes"])
            cur.execute("SELECT IdOrigen FROM dbo.ArcaDocumentos WHERE IdDocumento=?",c["idDocumento"])
            if cur.fetchone()[0]!=c["despues"]:raise ValueError("Cambió el enlace")
        if before!=control(cur):raise ValueError("Cambió un saldo")
        result={"backup":backup,"cambios":cambios}
        cur.execute("INSERT INTO dbo.AuditoriaCorrecciones(Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)",
                    regla,json.dumps(result),backup,"26enlaces PDF de retenciones corregidos aIdLiquidacion, identidad del mayor; sin cambios monetarios.")
    (EVID/"iva-enlaces-corregidos.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return {"corregidos":len(cambios),"backup":backup}


if __name__=="__main__":
    print(json.dumps(reparar_vinculos() if "--reparar-vinculos" in sys.argv else run("--aplicar" in sys.argv),default=str,ensure_ascii=False,indent=2))
