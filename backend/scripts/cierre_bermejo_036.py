"""036: cierre Bermejo autorizado por Sergio el 19/10/2026."""
from datetime import date
from decimal import Decimal
from src.db.connection import fetch_all,execute_write_transaction,_assert_target_is_wc
from src.features.vinculos.backup import backup_verificado
from src.features.revision_cuentas import fichas,evidencia

U="Sergio (036, cierre Bermejo 19/10/2026)"
NOTA="Cierre en cero autorizado por Sergio el 19/10/2026, sin resumen actualizado. OP 42211 y certificados respaldan pago completo de FC 00003-00000016. Redondeo por precision del precio unitario y fracciones historicas: $1,4736."

def main():
    _assert_target_is_wc()
    saldo=Decimal(str(fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS s FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?",(432,))[0]["s"])).quantize(Decimal("0.0001"))
    existentes=fetch_all("SELECT IdAjuste,Importe FROM dbo.AjustesCuentaCorriente WHERE IdContacto=? AND Motivo=?",(432,NOTA))
    if existentes:
        if len(existentes)!=1 or Decimal(str(existentes[0]["Importe"]))!=Decimal("1.4736"): raise RuntimeError("Ajuste existente diferente")
    else:
        if saldo!=Decimal("1.4736"): raise RuntimeError(f"Saldo inesperado {saldo}")
        print("Respaldo:",backup_verificado("cierre-bermejo-036"))
        execute_write_transaction([("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario) SELECT 432,?,'Deuda',?,?,? WHERE NOT EXISTS (SELECT 1 FROM dbo.AjustesCuentaCorriente WITH (UPDLOCK,HOLDLOCK) WHERE IdContacto=432 AND Motivo=?)",("2025-07-10",saldo,NOTA,U,NOTA))])
    corte=date(2026,9,30)
    if not fetch_all("SELECT IdSaldoExterno FROM dbo.RevisionSaldosExternos WHERE IdContacto=? AND Fuente='sin-estado' AND Anulado=0 AND Nota=?",(432,NOTA)):
        evidencia.crear_saldo_externo(432,corte,0,"Pesos","sin-estado",None,NOTA,U)
    fichas.confirmar_inventario(432,[
        {"tipo":"dropbox","disponible":True,"detalle":"Liquidacion FC 00003-00000016 y orden de pago OP-0000-00042211"},
        {"tipo":"certificado","disponible":True,"detalle":"Ganancias 2010-00010429 e IIBB 902-00013514, 10/07/2025, PDFs vinculados"},
        {"tipo":"extracto","disponible":True,"detalle":"BNA 9399 $3.500.000 y Galicia 2660 $45.761.085,14"},
        {"tipo":"estado-proveedor","disponible":False,"detalle":"Cierre autorizado sin resumen actualizado"},
    ],U)
    ficha=fichas.cambiar_estado(432,{"estado":"cerrada","nota":NOTA},U)
    saldo=Decimal(str(fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS s FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?",(432,))[0]["s"])).quantize(Decimal("0.01"))
    if saldo!=0: raise RuntimeError(f"Saldo no cero: {saldo}")
    print("Ficha:",ficha["estado"],"Saldo:",saldo)

if __name__=="__main__": main()
