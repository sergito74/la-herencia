"""Cierre Pedro Genta: redondeo autorizado por Sergio 19/10/2026."""
from datetime import date
from decimal import Decimal
from src.db.connection import fetch_all,execute_write_transaction,_assert_target_is_wc
from src.features.vinculos.backup import backup_verificado
from src.features.revision_cuentas import fichas,evidencia,criterios

U="Sergio (036, cierre Pedro Genta 19/10/2026)"
NOTA="Cierre en cero autorizado por Sergio el 19/10/2026. Redondeo residual $0,1106 tras cargar ajustes financieros 83464/85270 y certificados Ganancias 270060/279534. Operaciones de Giamigli figuran cerradas en portal deCampo a Campo; documentos y cobros conciliados."

def main():
    _assert_target_is_wc()
    saldo=Decimal(str(fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS s FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?",(320,))[0]["s"])).quantize(Decimal("0.0001"))
    previo=fetch_all("SELECT IdAjuste,Importe FROM dbo.AjustesCuentaCorriente WHERE IdContacto=? AND Motivo=?",(320,NOTA))
    if not previo:
        if saldo!=Decimal("0.1106"): raise RuntimeError(f"Saldo cambio: {saldo}")
        print("Respaldo:",backup_verificado("cierre-pedro-genta-036"))
        execute_write_transaction([("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario) SELECT 320,?,'Deuda',?,?,? WHERE NOT EXISTS (SELECT 1 FROM dbo.AjustesCuentaCorriente WITH (UPDLOCK,HOLDLOCK) WHERE IdContacto=320 AND Motivo=?)",("2026-07-22",saldo,NOTA,U,NOTA))])
    elif len(previo)!=1 or Decimal(str(previo[0]["Importe"]))!=Decimal("0.1106"):
        raise RuntimeError("Ajuste previo diferente")
    corte=date(2026,9,30)
    if not fetch_all("SELECT IdSaldoExterno FROM dbo.RevisionSaldosExternos WHERE IdContacto=? AND Anulado=0 AND Nota=?",(320,NOTA)):
        evidencia.crear_saldo_externo(320,corte,0,"Pesos","portal","deCampo a Campo: operaciones cerradas 31544, 17898, 7067, 7199, 7204; consulta 19/10/2026",NOTA,U)
    fichas.confirmar_inventario(320,[
        {"tipo":"dropbox","disponible":True,"detalle":"Liquidaciones 2017, 2022 y 2026; ajustes financieros 83464/85270 guardados en Ventas/04 2026 - 03 2027"},
        {"tipo":"certificado","disponible":True,"detalle":"Ganancias 2023 ya contabilizadas y certificados 2026 270060/279534 registrados con PDF"},
        {"tipo":"extracto","disponible":True,"detalle":"Cobros BNA/Galicia conciliados contra liquidaciones y ajustes"},
        {"tipo":"estado-proveedor","disponible":True,"detalle":"Consulta de operaciones cerradas del portal; no es un resumen PDF actualizado"},
    ],U)
    faltan=criterios.faltantes_para_cerrar(criterios.evaluar(fichas.cargar_contexto(320,corte)["criterios_ctx"]))
    if faltan: raise RuntimeError(str(faltan))
    f=fichas.cambiar_estado(320,{"estado":"cerrada","nota":NOTA},U)
    print("Ficha:",f["estado"],"saldo:",f.get("saldoAlCorte"))

if __name__=="__main__": main()
