"""Adicional acordado de Marcelo, fórmula de Liquidaciones Encargado AG:AJ.
Usa neto del recibo, excluye la bonificación ya registrada. Nunca crea pagos.
"""
from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING
from datetime import datetime
import re

from src.db.connection import atomic_reconciliation, fetch_one, execute_write
from src.features.remuneraciones import repository as repo


def multiplo_cinco(valor):
    return (Decimal(str(valor))/Decimal(5)).quantize(Decimal(1), ROUND_HALF_UP)*Decimal(5)


def calcular(neto):
    neto=Decimal(str(neto)).quantize(Decimal("0.01"),ROUND_HALF_UP)
    if neto<0:
        raise ValueError("El neto del recibo no puede ser negativo")
    adicional=multiplo_cinco(neto*Decimal("0.30"))
    feriados=multiplo_cinco(neto*Decimal("0.085"))
    subtotal=adicional+feriados
    total=(subtotal/Decimal(100)).quantize(Decimal(1),ROUND_CEILING)*Decimal(100)
    redondeo=total-subtotal
    if total<0 or total>Decimal("9999999999999999.99"):
        raise ValueError("El adicional resultante no es válido")
    return {"netoRecibo":float(neto),"porcentajeAdicional":30,"porcentajeFeriados":8.5,
            "adicional":float(adicional),"feriados":float(feriados),"redondeo":float(redondeo),
            "totalAdicional":float(total),"totalACobrar":float(neto+total)}


def obtener(id_salario):
    fila=fetch_one("SELECT r.IdContacto AS idContacto,r.[Periodo liquidado] AS periodo,"
                   "("+repo._IMPORTE_SQL+")-ISNULL(r.[Bonificacion adicional],0) AS neto,"
                   "ISNULL(r.[Bonificacion adicional],0) AS registrado,c.[CUIT/CUIL] AS cuil "
                   "FROM dbo.Remuneraciones r JOIN dbo.Contactos c ON c.IdContacto=r.IdContacto WHERE r.IdSalario=?",(id_salario,))
    if not fila:
        return None
    if fila["idContacto"]!=374 or str(fila["cuil"]).replace("-", "").replace(" ", "")!="20132391670":
        raise ValueError("Este cálculo corresponde al adicional de Marcelo Sierra")
    periodo = str(fila["periodo"]).strip()
    meses = ("Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre")
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}",periodo):
        fecha = datetime.strptime(periodo,"%d/%m/%Y")
        periodo = f"{meses[fecha.month-1]} {fecha.year}"
    if not re.fullmatch("(?:"+"|".join(meses)+r") \d{4}", periodo):
        raise ValueError("El cálculo se abre desde una liquidación mensual del recibo de sueldo")
    if str(fila["periodo"]).casefold().startswith("adicional fuera de recibo"):
        raise ValueError("Esta fila ya es un adicional fuera de recibo; el cálculo se abre desde el recibo de sueldo")
    separados=fetch_one("SELECT IdSalario AS id,("+repo._IMPORTE_SQL+") AS importe FROM dbo.Remuneraciones r "
                        "WHERE IdContacto=374 AND [Periodo liquidado]=?",("Adicional fuera de recibo "+periodo,))
    guardado=fetch_one("SELECT Redondeo AS redondeo FROM dbo.RemuneracionesAdicionalCalculo WHERE IdSalario=?",(id_salario,))
    return {"idSalario":id_salario,"periodo":fila["periodo"],"registrado":float(fila["registrado"]),
            "tieneCalculo":guardado is not None,"adicionalSeparado":separados["id"] if separados else None,
            "registradoSeparado":float(separados["importe"]) if separados else 0,
            "puedeGuardar":not separados,**calcular(fila["neto"])}


@atomic_reconciliation
def guardar(id_salario, usuario):
    dato=obtener(id_salario)
    if dato is None:
        return None
    if not dato["puedeGuardar"]:
        raise ValueError("El adicional de este período ya está registrado por separado; no se duplica")
    usado=fetch_one("SELECT ISNULL(SUM(Importe),0) AS importe FROM dbo.TrabajosEventualesVinculos WHERE IdSalario=?",(id_salario,))["importe"]
    if Decimal(str(usado)) > Decimal(str(dato["totalACobrar"])):
        raise ValueError("El nuevo total queda por debajo de los trabajos vinculados")
    # Una sola bonificación en el registro existente; las cuentas la computan una vez.
    execute_write("UPDATE dbo.Remuneraciones SET [Bonificacion adicional]=? WHERE IdSalario=? AND IdContacto=374",
                  (dato["totalAdicional"],id_salario))
    params=(dato["netoRecibo"],dato["adicional"],dato["feriados"],dato["redondeo"],dato["totalAdicional"],usuario[:100],id_salario)
    if fetch_one("SELECT 1 AS x FROM dbo.RemuneracionesAdicionalCalculo WHERE IdSalario=?",(id_salario,)):
        execute_write("UPDATE dbo.RemuneracionesAdicionalCalculo SET NetoRecibo=?,Adicional=?,Feriados=?,Redondeo=?,Total=?,"
                      "Usuario=?,Actualizado=SYSDATETIME() WHERE IdSalario=?",params)
    else:
        execute_write("INSERT INTO dbo.RemuneracionesAdicionalCalculo (NetoRecibo,Adicional,Feriados,Redondeo,Total,Usuario,IdSalario) "
                      "VALUES (?,?,?,?,?,?,?)",params)
    from src.features.trabajos_eventuales.repository import auditar
    auditar(None,"adicional-sierra",dato,usuario)
    from src.features.auditoria_cuentas.bimonetaria import invalidar
    invalidar()
    return obtener(id_salario)
