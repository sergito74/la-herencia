"""Diez obligaciones F931 oficiales, PDF vinculados y pagos repartidos sin duplicarlos.

Inspección por defecto. --aplicar: respaldo, transacción, auditoría e invariantes.
Fuentes descargadas en arca-continuacion-20261025; nunca guarda credenciales.
"""
import argparse
from datetime import datetime
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import re
import shutil

from src.db.connection import _reconciliation_connection, reconciliation_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_corrientes import arca
from src.features.cuentas_corrientes.arca_documentos import RAIZ, verificar_archivo
from src.features.vinculos.backup import backup_verificado
from scripts.vincular_tres_pagos_condominio_036 import control

ROOT = Path(__file__).resolve().parents[2]
EVIDENCIA = ROOT / "backups/arca-continuacion-20261025"
REGLA = "arca-f931-diez-pendientes-portal-036"
BANCOS = {"05/2025":2608,"06/2025":2667,"07/2025":2734,"08/2025":2776,"09/2025":2825,
          "01/2026":3046,"02/2026":3086,"03/2026":3138,"04/2026":3210,"05/2026":3269,"12/2025":2991}


def guardar_json(nombre, datos):
    (EVIDENCIA / nombre).write_text(json.dumps(datos,default=str,ensure_ascii=False,indent=2),encoding="utf-8")


def fuentes():
    import pdfplumber
    formularios = json.loads((EVIDENCIA/"f931-formularios.json").read_text(encoding="utf-8"))
    comprobantes = json.loads((EVIDENCIA/"comprobantes.json").read_text(encoding="utf-8"))
    resultado=[]
    for f in formularios:
        per=f["periodo"]
        if per not in BANCOS:
            continue
        anno,mes=per[3:],per[:2]
        docs=[{"archivo":f["archivo"],"sha256":f["sha256"],"tipo":"F931 — copia del portal","original":False}]
        pagos=[]
        for tipo in ("acuse","pago-vep"):
            c=next(x for x in comprobantes if x["periodo"]==per and x["tipo"]==tipo)
            p=EVIDENCIA/c["archivo"]
            if hashlib.sha256(p.read_bytes()).hexdigest()!=c["sha256"]:
                raise ValueError("Cambió un PDF descargado")
            with pdfplumber.open(p) as pdf:
                texto="\n".join(page.extract_text() or "" for page in pdf.pages)
            if "30-71211460-2" not in texto or anno+"-"+mes not in texto:
                raise ValueError("PDF de otro CUIT/período")
            numero = re.search(r"Nro\. VEP:\s*(\d+)",texto)
            if tipo=="pago-vep":
                monto=re.search(r"IMPORTE PAGADO\s*\$([\d.,]+)",texto)
                fecha=re.search(r"Fecha de Pago:\s*(\d{4}-\d{2}-\d{2})",texto)
                importe=D(monto[1].replace(".","").replace(",","."))
                if importe!=D(f["total"]):raise ValueError("VEP y DDJJ no coinciden")
                pagos.append({"numero":numero[1],"importe":importe,"fecha":fecha[1]})
            docs.append({"archivo":c["archivo"],"sha256":c["sha256"],"tipo":"Acuse de presentación" if tipo=="acuse" else "VEP pagado",
                         "original":True,"numero":numero[1] if numero else None})
        bank=read("SELECT IdMovimiento,Fecha,[Débitos] debito,[Créditos] credito,IdContacto FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=?",(BANCOS[per],))[0]
        if bank["IdContacto"]!=119 or bank["debito"]<pagos[0]["importe"] or bank["credito"] or str(bank["Fecha"])[:10]!=pagos[0]["fecha"]:
            raise ValueError("No coincide el banco con el pago oficial")
        for doc in docs:
            original=EVIDENCIA/doc["archivo"]
            if hashlib.sha256(original.read_bytes()).hexdigest()!=doc["sha256"]:raise ValueError("Cambió formulario")
            destino=RAIZ/"Cargas Sociales"/anno/doc["archivo"]
            if destino.exists() and hashlib.sha256(destino.read_bytes()).hexdigest()!=doc["sha256"]:
                raise ValueError("Existe otro documento con ese nombre; no sobrescribir")
            destino.parent.mkdir(parents=True,exist_ok=True)
            if not destino.exists():shutil.copy2(original,destino)
            verificar_archivo(destino,doc["sha256"])
            doc["ruta"]=str(destino)
        resultado.append({**f,"fecha":datetime.strptime(f["generacion"],"%d/%m/%Y %H:%M:%S").date(),
                          "pago":pagos[0],"banco":bank,"documentos":docs})
    if set(p["periodo"] for p in resultado)!=set(BANCOS):raise ValueError("Faltan documentos de algún período")
    return resultado


def run(aplicar=False):
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'",(REGLA,)):
        return {"estado":"ya_aplicado_sin_escrituras"}
    plan=fuentes()
    impuestos=read("SELECT * FROM dbo.Impuestos WHERE IdOrganismo=119 ORDER BY IdImpuesto")
    for p in plan:
        periodo=p["periodo"].replace("/"," ")
        existentes=[i for i in impuestos if i["IdTipoImpuesto"]==2 and (i["Periodo liquidado"] or "").replace("/"," ").replace("-"," ")==periodo]
        if p["periodo"]=="12/2025":
            if len(existentes)!=1 or existentes[0]["Importe"]!=D(p["total"]):raise ValueError("Diciembre existente no coincide")
            p["idImpuesto"]=existentes[0]["IdImpuesto"]
        elif existentes:raise ValueError("Ya hay obligación de un período faltante; no duplicar")
    total=sum(D(p["total"]) for p in plan if "idImpuesto" not in p)
    guardar_json("punto1-plan.json",plan)
    if not aplicar:return {"estado":"inspeccion","obligacionesNuevas":10,"importe":total,"periodosConPDF":11}
    backup=backup_verificado("arca-f931-portal-036")
    resultado={"respaldo":backup,"plan":plan,"totalNuevas":total}
    with reconciliation_transaction():
        cur=_reconciliation_connection.get().cursor()
        before=control(cur)
        if read("SELECT * FROM dbo.Impuestos WHERE IdOrganismo=119 ORDER BY IdImpuesto")!=impuestos:raise ValueError("Cambió el inventario de impuestos")
        for p in plan:
            banco_actual=read("SELECT IdMovimiento,Fecha,[Débitos] debito,[Créditos] credito,IdContacto FROM dbo.[Movimientos Galicia] WITH (HOLDLOCK) WHERE IdMovimiento=?",(p["banco"]["IdMovimiento"],))
            if banco_actual != [p["banco"]]:raise ValueError("Cambió el banco desde la inspección")
            principal=p["documentos"][0]["ruta"]
            if "idImpuesto" not in p:
                cur.execute("INSERT INTO dbo.Impuestos (Fecha,IdOrganismo,IdTipoImpuesto,[Periodo liquidado],[Numero de documento],Importe,[Documento Original]) OUTPUT INSERTED.IdImpuesto VALUES (?,119,2,?,?,?,?)",
                            str(p["fecha"]),p["periodo"].replace("/"," "),"VEP "+p["pago"]["numero"],str(D(p["total"])),principal)
                p["idImpuesto"]=cur.fetchone()[0]
            for doc in p["documentos"]:
                claves=[("Impuestos",p["idImpuesto"])]
                if doc["tipo"]=="VEP pagado":claves.append(("Galicia",p["banco"]["IdMovimiento"]))
                for origen,ident in claves:
                    cur.execute("INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario) VALUES (?,?,?,?,?,?,?,?,?)",
                                origen,ident,doc["tipo"],p["periodo"],doc.get("numero"),doc["ruta"],doc["sha256"],doc["original"],"Codex036")
            credito=p["banco"]["debito"]
            partes=[{"subcuenta":"cargas-sociales","deuda":D(0),"credito":D(p["total"])}]
            if credito>D(p["total"]):partes.append({"subcuenta":"por-identificar","deuda":D(0),"credito":credito-D(p["total"])})
            version=read("SELECT TOP(1) IdClasificacion version FROM dbo.ArcaClasificaciones WHERE Origen='Galicia' AND IdOrigen=? ORDER BY IdClasificacion DESC",(p["banco"]["IdMovimiento"],))
            if version:raise ValueError("Hay clasificación previa de un pago; revisar sin sobrescribir")
            arca.guardar("Galicia",p["banco"]["IdMovimiento"],0,partes,"F931 y VEP pagado oficial del período "+p["periodo"]+"; excedente del débito separado, sin inventar aplicación fiscal.","Codex036")
        after=control(cur)
        esperado=dict(before["cuentas"]);esperado[119]-=total
        if esperado!=dict(after["cuentas"]) or before["cajas"]!=after["cajas"] or before["socios"]!=after["socios"]:
            raise ValueError("Cambió una cuenta, caja o socio fuera de lo previsto")
        resultado.update(saldoAntes=dict(before["cuentas"])[119],saldoDespues=dict(after["cuentas"])[119])
        cur.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)",
                    REGLA,json.dumps(resultado,default=str,ensure_ascii=False),backup,f"10 F931 oficiales por {total}; 44 vínculos PDF, 11 pagos clasificados con excedentes separados. Sin pagos nuevos ni cambios a socios/cajas.")
    guardar_json("punto1-aplicado.json",resultado)
    return {"estado":"aplicado","obligaciones":10,"importe":total,"saldo":resultado["saldoDespues"],"respaldo":backup}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar",action="store_true")
    print(json.dumps(run(parser.parse_args().aplicar),default=str,ensure_ascii=False,indent=2))
