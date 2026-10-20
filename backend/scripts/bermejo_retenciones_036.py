"""036: reconstrucción documental Bermejo 432, 19/10/2026; no cierra ficha."""
from decimal import Decimal
from pathlib import Path
from src.db.connection import fetch_all,execute_write_transaction,_assert_target_is_wc
from src.features.vinculos.backup import backup_verificado
from src.features.revision_cuentas import evidencia

PDF=Path(r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Ventas\Retenciones 04 2025 - 03 2026\Certificado de Retencion de Ganancias Firma[1].pdf")
U="Sergio (continuidad 036, 19/10/2026)"
CERTS=[("2010-00010429","Cert. Retencion Ganancias",Decimal("909795.73")),("902-00013514","Cert. Retencion IIBB",Decimal("342853.40"))]

def main():
    _assert_target_is_wc()
    if not PDF.is_file(): raise RuntimeError("Falta PDF")
    st=[]
    for n,t,i in CERTS:
        r=fetch_all("SELECT Importe,Fecha FROM dbo.[Retenciones Ventas Hacienda] WHERE IdContacto=? AND [Nro Documento]=?",(432,n))
        if r:
            if len(r)!=1 or Decimal(str(r[0]["Importe"]))!=i or str(r[0]["Fecha"])[:10]!="2025-07-10": raise RuntimeError("Certificado diferente")
        else:
            st.append(("INSERT INTO dbo.[Retenciones Ventas Hacienda] (Id,Fecha,IdContacto,Documento,[Nro Documento],Importe,Imagen) SELECT (SELECT ISNULL(MAX(Id),0)+1 FROM dbo.[Retenciones Ventas Hacienda] WITH (UPDLOCK,HOLDLOCK)),?,?,?,?,?,? WHERE NOT EXISTS (SELECT 1 FROM dbo.[Retenciones Ventas Hacienda] WITH (UPDLOCK,HOLDLOCK) WHERE IdContacto=? AND [Nro Documento]=?)",("2025-07-10",432,t,n,i,str(PDF),432,n)))
    m=fetch_all("SELECT IdContacto,Importe FROM dbo.[Movimientos BNA] WHERE IdMovimientoBNA=?",(9399,))[0]
    if m["IdContacto"]==0:
        if Decimal(str(m["Importe"]))!=Decimal("3500000"): raise RuntimeError("Banco diferente")
        st.extend([
            ("INSERT INTO dbo.AuditoriaRevisionesHistorial (IdContacto,Accion,Detalle,Usuario) SELECT 432,'asignacion-contacto',?,? FROM dbo.[Movimientos BNA] WITH (UPDLOCK,HOLDLOCK) WHERE IdMovimientoBNA=9399 AND IdContacto=0 AND Importe=3500000",('{"origen":"Banco Nacion","idOrigen":9399,"idContactoAnterior":0,"idContactoNuevo":432,"motivo":"OP-0000-00042211, pago 85394 del 10/07/2025: BNA $3.500.000 y Galicia $45.761.085,14; ingreso BNA sin contacto, misma fecha e importe. Reversible restaurando IdContacto=0 y Contacto=NULL."}',U)),
            ("UPDATE dbo.[Movimientos BNA] SET IdContacto=432,Contacto='S.A. Exp. De Campos y Montes del Rio Bermejo' WHERE IdMovimientoBNA=9399 AND IdContacto=0 AND Importe=3500000",())])
    elif m["IdContacto"]!=432: raise RuntimeError("Ingreso ya asignado a otro contacto")
    if fetch_all("SELECT Estado FROM dbo.RevisionFichas WHERE IdContacto=? AND Estado IN ('cerrada','cerrada-con-excepcion')",(432,)): raise RuntimeError("Cuenta cerrada")
    if st:
        print("Respaldo:",backup_verificado("bermejo-retenciones-036"))
        execute_write_transaction(st)
    marcas=evidencia.leer_marcas(432)
    for n,_,_ in CERTS:
        r=fetch_all("SELECT Id FROM dbo.[Retenciones Ventas Hacienda] WHERE IdContacto=? AND [Nro Documento]=?",(432,n))[0]
        if ("ret.-ventas-hacienda",r["Id"]) not in marcas:
            evidencia.guardar_marca(432,"ret.-ventas-hacienda",r["Id"],"venta-cargada",None,"pdf",f"Certificado {n}, OP 42211, venta 00003-00000016",U,"venta-hacienda",134)
    print("Saldo:",fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS saldo FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?",(432,)))

if __name__=="__main__": main()
