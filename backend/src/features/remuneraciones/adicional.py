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
    pago_caja=fetch_one("SELECT TOP 1 m.IdMovimiento, m.Fecha, m.Caja, m.Cuenta, m.Importe, m.Concepto, m.IdPagoEfectivo "
                        "FROM dbo.MovimientosCajaEfectivo m "
                        "WHERE m.IdContactoRelacionado=374 AND m.Anulada=0 AND m.Concepto LIKE ? "
                        "ORDER BY m.Fecha DESC", (f"%Adicional Sueldo Marcelo {periodo}%",))
    pago_dict = None
    if pago_caja:
        pago_dict = dict(pago_caja)
        if pago_dict.get("Fecha"):
            pago_dict["Fecha"] = str(pago_dict["Fecha"])[:10]
    return {"idSalario":id_salario,"periodo":fila["periodo"],"registrado":float(fila["registrado"]),
            "tieneCalculo":guardado is not None,"adicionalSeparado":separados["id"] if separados else None,
            "registradoSeparado":float(separados["importe"]) if separados else 0,
            "puedeGuardar":not separados,
            "pagoCaja": pago_dict,
            **calcular(fila["neto"])}


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



@atomic_reconciliation
def registrar_pago_caja_giamigli(id_salario, fecha, cuenta, usuario):
    dato = obtener(id_salario)
    if not dato:
        raise ValueError("Liquidación no encontrada")
    if dato["pagoCaja"]:
        raise ValueError("El pago en caja ya se encuentra registrado para esta liquidación")
    total_adicional = dato["totalAdicional"]
    if total_adicional <= 0:
        raise ValueError("El adicional a pagar debe ser mayor a cero")

    cuenta_b = "B" if cuenta.upper() == "B" else "A"
    cuenta_legacy = "Blue" if cuenta_b == "B" else "White"
    concepto = f"Adicional Sueldo Marcelo {dato['periodo']}"
    
    # 1. Movimiento en [Pagos efectivo] (impacta en cta cte de Marcelo Sierra, idContacto=374)
    # Importe imputado positivo = credito en cta cte (cancela deuda de remuneraciones)
    sql_pago = (
        "INSERT INTO dbo.[Pagos efectivo] "
        "(IdContacto, IdTipoMovimiento, IdFormaPago, Fecha, Cuenta, Caja, [Importe imputado]) "
        "OUTPUT INSERTED.IdPagoEfectivo "
        "VALUES (374, 1, 3, ?, ?, 'GiamigliSA', ?)"
    )
    from src.db.connection import execute_insert_returning_id
    id_pago_efectivo = execute_insert_returning_id(sql_pago, (fecha, cuenta_legacy, total_adicional))

    # 2. Movimiento en MovimientosCajaEfectivo (impacta en arqueo y saldo de Caja Giamigli)
    # Importe negativo = egreso de caja
    sql_caja = (
        "INSERT INTO dbo.MovimientosCajaEfectivo "
        "(Caja, Fecha, Concepto, Detalle, Importe, Cuenta, FormaPago, IdContactoRelacionado, Usuario, IdPagoEfectivo, Tipo) "
        "OUTPUT INSERTED.IdMovimiento "
        "VALUES ('GiamigliSA', ?, ?, 'Liquidación Marcelo Sierra adicional fuera de recibo', ?, ?, 'Efectivo', 374, ?, ?, 'pago_sueldo_adicional')"
    )
    id_mov = execute_insert_returning_id(sql_caja, (fecha, concepto, -total_adicional, cuenta_b, usuario[:100], id_pago_efectivo))

    from src.features.trabajos_eventuales.repository import auditar
    auditar(None, "pago-adicional-caja-giamigli", {
        "idSalario": id_salario,
        "idMovimientoCaja": id_mov,
        "idPagoEfectivo": id_pago_efectivo,
        "importe": total_adicional,
        "fecha": str(fecha),
        "cuenta": cuenta_b
    }, usuario)

    from src.features.auditoria_cuentas.bimonetaria import invalidar
    invalidar()
    return obtener(id_salario)
