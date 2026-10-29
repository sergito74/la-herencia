"""045: esquema/importación de trabajos, solo WC. Simula por defecto; --aplicar toma respaldo.
No modifica liquidaciones, pagos ni Excel. Resguarda hojas auxiliares como evidencia.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from src.db.connection import get_connection, fetch_all, fetch_one, execute_write, execute_insert_returning_id, reconciliation_transaction
from src.features.contactos.repository import create_contacto
from src.features.remuneraciones import repository as salarios
from src.features.trabajos_eventuales import repository as trabajos
from src.features.vinculos.backup import backup_verificado

FUENTE = Path.home() / "Documents/La Herencia/Administracion y gestion/Personal/Planilla trabajos eventuales.xlsx"
CLAVE = "planilla-eventuales-045"
DDL = [
"""IF OBJECT_ID('dbo.RemuneracionesAdicionalCalculo','U') IS NULL CREATE TABLE dbo.RemuneracionesAdicionalCalculo (
 IdSalario int PRIMARY KEY,NetoRecibo decimal(18,2) NOT NULL,Adicional decimal(18,2) NOT NULL,
 Feriados decimal(18,2) NOT NULL,Redondeo decimal(18,2) NOT NULL,Total decimal(18,2) NOT NULL,
 Usuario nvarchar(100) NOT NULL,Actualizado datetime2 NOT NULL DEFAULT SYSDATETIME())""",
"""IF OBJECT_ID('dbo.TrabajosEventuales','U') IS NULL CREATE TABLE dbo.TrabajosEventuales (
 IdTrabajo int IDENTITY PRIMARY KEY,IdContacto int NOT NULL,Fecha date NOT NULL,Descripcion nvarchar(500) NOT NULL,
 Dias decimal(12,4) NOT NULL CHECK(Dias>=0),Jornal decimal(18,2) NOT NULL CHECK(Jornal>=0),
 Viaticos decimal(18,2) NOT NULL CHECK(Viaticos>=0),Redondeo decimal(18,2) NOT NULL DEFAULT 0,
 Total decimal(18,2) NOT NULL CHECK(Total>=0),EstadoPago varchar(10) NOT NULL CHECK(EstadoPago IN ('Pendiente','Pagado')),
 NumeroRecibo nvarchar(40) NULL,Observaciones nvarchar(1000) NULL,OrigenClave nvarchar(180) NULL,
 Usuario nvarchar(100) NOT NULL,Creado datetime2 NOT NULL DEFAULT SYSDATETIME(),Actualizado datetime2 NOT NULL DEFAULT SYSDATETIME(),
 CHECK(Total=ROUND(Dias*Jornal+Viaticos,2)+Redondeo))""",
"""IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE name='UX_TrabajosEventuales_Origen')
 CREATE UNIQUE INDEX UX_TrabajosEventuales_Origen ON dbo.TrabajosEventuales(OrigenClave) WHERE OrigenClave IS NOT NULL""",
"""IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE name='IX_TrabajosEventuales_ContactoFecha')
 CREATE INDEX IX_TrabajosEventuales_ContactoFecha ON dbo.TrabajosEventuales(IdContacto,Fecha)""",
"""IF OBJECT_ID('dbo.TrabajosEventualesVinculos','U') IS NULL CREATE TABLE dbo.TrabajosEventualesVinculos (
 IdVinculo int IDENTITY PRIMARY KEY,IdTrabajo int NOT NULL REFERENCES dbo.TrabajosEventuales(IdTrabajo),
 IdSalario int NOT NULL,Importe decimal(18,2) NOT NULL CHECK(Importe>0),Usuario nvarchar(100) NOT NULL,
 Creado datetime2 NOT NULL DEFAULT SYSDATETIME(),UNIQUE(IdTrabajo,IdSalario))""",
"""IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE name='IX_TrabajosEventualesVinculos_Salario')
 CREATE INDEX IX_TrabajosEventualesVinculos_Salario ON dbo.TrabajosEventualesVinculos(IdSalario)""",
"""IF OBJECT_ID('dbo.TrabajosEventualesAuditoria','U') IS NULL CREATE TABLE dbo.TrabajosEventualesAuditoria (
 IdAuditoria int IDENTITY PRIMARY KEY,IdTrabajo int NULL,Accion varchar(30) NOT NULL,Datos nvarchar(max) NOT NULL,
 Usuario nvarchar(100) NOT NULL,Fecha datetime2 NOT NULL DEFAULT SYSDATETIME())""",
"""IF OBJECT_ID('dbo.TrabajosEventualesFuentes','U') IS NULL CREATE TABLE dbo.TrabajosEventualesFuentes (
 Clave nvarchar(180) PRIMARY KEY,Sha256 char(64) NOT NULL,Ruta nvarchar(500) NOT NULL,Datos nvarchar(max) NOT NULL,
 Creado datetime2 NOT NULL DEFAULT SYSDATETIME())""",
]


def leer_planilla(ruta: Path):
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    hojas = {}
    with zipfile.ZipFile(ruta) as z:
        shared = ["".join(s.itertext()) for s in ET.fromstring(z.read("xl/sharedStrings.xml"))]
        book = ET.fromstring(z.read("xl/workbook.xml"))
        rels = {r.attrib["Id"]: r.attrib["Target"] for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
        for sheet in book.find("m:sheets", ns):
            rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = rels[rid]
            nombre_xml = target.lstrip("/") if target.startswith("/") else "xl/"+target
            filas = []
            for row in ET.fromstring(z.read(nombre_xml)).findall("m:sheetData/m:row", ns):
                valores = {"fila": int(row.attrib["r"])}
                for cell in row:
                    val = cell.find("m:v", ns)
                    if val is not None:
                        col = re.sub(r"\d", "", cell.attrib["r"])
                        valores[col] = shared[int(val.text)] if cell.get("t") == "s" else val.text
                if len(valores)>1:
                    filas.append(valores)
            hojas[sheet.attrib["name"]] = filas
    personas = {f["A"]: f["B"].replace("-", "").replace(" ", "") for f in hojas["Empleado"] if f["fila"]>1}
    registros = []
    for f in hojas["Trabajos"]:
        if f["fila"] == 1 or not f.get("A"):
            continue
        if f.get("B") not in personas:
            raise ValueError("Trabajador sin CUIT en la fuente")
        dias, jornal, viaticos, total = (Decimal(f.get(c,"0")) for c in ("D","E","G","H"))
        redondeo = total - trabajos.dinero(dias*jornal+viaticos)
        if (total != 0 and trabajos.total_trabajo(dias,jornal,viaticos,redondeo) != total) or f.get("I") not in ("Pendiente","Pagado"):
            raise ValueError(f"Fila {f['fila']} inválida")
        registros.append({"origen": f"{CLAVE}:Trabajos:{f['fila']}","nombre": f["B"],"cuit":personas[f["B"]],
            "fecha": (datetime(1899,12,30)+timedelta(days=int(f["A"]))),"descripcion": f.get("C", "Sin descripción en la planilla"),"dias":dias,
            "jornal":jornal,"viaticos":viaticos,"redondeo":redondeo,"total":total,"estado":f["I"],"recibo":f.get("J")})
    return registros, hojas


def vinculos_seguros():
    """Solo grupo mensual exacto contra un único recibo del período, o jornal con fecha explícita."""
    nuevos = []
    todos = fetch_all("SELECT IdTrabajo AS id,IdContacto AS contacto,Fecha AS fecha,Total AS total FROM dbo.TrabajosEventuales "
                      "WHERE OrigenClave LIKE ? AND NOT EXISTS (SELECT 1 FROM dbo.TrabajosEventualesVinculos v "
                      "WHERE v.IdTrabajo=dbo.TrabajosEventuales.IdTrabajo)", (CLAVE+":%",))
    grupos = {}
    for t in todos:
        fecha = datetime.fromisoformat(str(t["fecha"])[:10])
        grupos.setdefault((t["contacto"],fecha.year,fecha.month), []).append(t)
    meses = ("Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre")
    for (contacto,anio,mes), ts in grupos.items():
        candidatos = fetch_all("SELECT r.IdSalario AS id,("+salarios._IMPORTE_SQL+") AS neto "
                               "FROM dbo.Remuneraciones r WHERE IdContacto=? AND [Periodo liquidado]=? "
                               "AND NOT EXISTS (SELECT 1 FROM dbo.TrabajosEventualesVinculos v WHERE v.IdSalario=r.IdSalario)",
                               (contacto,f"{meses[mes-1]} {anio}"))
        suma = sum(trabajos.dinero(t["total"]) for t in ts)
        if len(candidatos)==1 and trabajos.dinero(candidatos[0]["neto"]) == suma:
            for t in ts:
                if trabajos.dinero(t["total"]) == 0:
                    continue
                trabajos.vincular(t["id"],candidatos[0]["id"],t["total"],"Importación 045 (período/neto exactos)")
                nuevos.append({"trabajo":t["id"],"liquidacion":candidatos[0]["id"],"importe":t["total"]})
    return nuevos


def main(ruta=FUENTE, aplicar=False):
    registros, hojas = leer_planilla(ruta)
    total = sum(r["total"] for r in registros)
    print(f"Fuente: {len(registros)} trabajos, {len(set(r['cuit'] for r in registros))} personas; total {total:.2f}")
    contactos = {}
    faltantes = []
    for r in registros:
        if r["cuit"] in contactos:
            continue
        filas = fetch_all("SELECT IdContacto AS id,[Tipo Contacto] AS tipo FROM dbo.Contactos "
                          "WHERE REPLACE(REPLACE([CUIT/CUIL],'-',''),' ','')=?", (r["cuit"],))
        if len(filas)>1 or (filas and filas[0]["tipo"]!='Empleado'):
            raise ValueError(f"Revisar identidad fiscal de {r['nombre']}")
        contactos[r["cuit"]] = filas[0]["id"] if filas else None
        if not filas:
            faltantes.append({"nombre":r["nombre"],"cuit":r["cuit"]})
    existe = fetch_one("SELECT OBJECT_ID('dbo.TrabajosEventuales','U') AS id")["id"]
    previos = {f["origen"] for f in fetch_all("SELECT OrigenClave AS origen FROM dbo.TrabajosEventuales WHERE OrigenClave LIKE ?",(CLAVE+":%",))} if existe else set()
    print("Trabajos nuevos:",sum(r["origen"] not in previos for r in registros),"Contactos faltantes:",faltantes)
    if not aplicar:
        return
    respaldo = backup_verificado("trabajos-eventuales-045")
    print("Respaldo verificado:",respaldo)
    carpeta = Path(__file__).resolve().parents[2]/"backups/trabajos-eventuales-045"
    carpeta.mkdir(parents=True,exist_ok=True)
    sha = hashlib.sha256(ruta.read_bytes()).hexdigest()
    copia = carpeta/f"fuente-{sha[:12]}.xlsx"
    if not copia.exists():
        shutil.copy2(ruta,copia)
    if hashlib.sha256(copia.read_bytes()).hexdigest()!=sha:
        raise ValueError("No se pudo verificar la copia de la fuente")
    with reconciliation_transaction():
        with get_connection(readonly=False) as conn:
            for sql in DDL:
                conn.cursor().execute(sql)
        for persona in faltantes:
            contactos[persona["cuit"]] = create_contacto(persona["nombre"],"Empleado",persona["cuit"],False)
        fuente = fetch_one("SELECT Sha256 AS sha FROM dbo.TrabajosEventualesFuentes WHERE Clave=?",(CLAVE,))
        if not fuente:
            execute_write("INSERT INTO dbo.TrabajosEventualesFuentes(Clave,Sha256,Ruta,Datos) VALUES (?,?,?,?)",
                          (CLAVE,sha,str(copia),json.dumps(hojas,ensure_ascii=False)))
        elif fuente["sha"] != sha:
            execute_write("UPDATE dbo.TrabajosEventualesFuentes SET Sha256=?, Ruta=?, Datos=? WHERE Clave=?", (sha, str(copia), json.dumps(hojas, ensure_ascii=False), CLAVE))
        for r in registros:
            if fetch_one("SELECT 1 AS x FROM dbo.TrabajosEventuales WHERE OrigenClave=?",(r["origen"],)):
                continue
            i = execute_insert_returning_id("INSERT INTO dbo.TrabajosEventuales "
                "(IdContacto,Fecha,Descripcion,Dias,Jornal,Viaticos,Redondeo,Total,EstadoPago,NumeroRecibo,OrigenClave,Usuario) "
                "OUTPUT INSERTED.IdTrabajo VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (contactos[r["cuit"]],r["fecha"],r["descripcion"],r["dias"],r["jornal"],r["viaticos"],r["redondeo"],r["total"],
                 r["estado"],r["recibo"],r["origen"],"Importación planilla 045"))
            trabajos.auditar(i,"importar",r,"Importación planilla 045")
        vinculos = vinculos_seguros()
    informe = {"respaldo":respaldo,"fuente":str(copia),"trabajos":len(registros),"total":str(total),
               "contactosNuevos":faltantes,"vinculos":vinculos,"resumen":trabajos.listar(page_size=1)["resumen"]}
    (carpeta/"resultado.json").write_text(json.dumps(informe,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    print(json.dumps(informe,ensure_ascii=False,default=str))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--aplicar",action="store_true")
    p.add_argument("--fuente",type=Path,default=FUENTE)
    a=p.parse_args()
    main(a.fuente,a.aplicar)
