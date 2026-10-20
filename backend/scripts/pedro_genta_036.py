"""036: Pedro Genta, documentos financieros obtenidos del portal, 19/10/2026.

No cierra la ficha: presenta saldo residual para aprobación de Sergio.
Las retenciones 2023 ya están como pagos efectivo: no se duplican.
"""
from datetime import date
from decimal import Decimal
from pathlib import Path
from src.db.connection import fetch_all,execute_write_transaction,_assert_target_is_wc
from src.features.vinculos.backup import backup_verificado
from src.features.ventas_hacienda import repository as ventas
from src.features.revision_cuentas import evidencia

ROOT=Path(r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Ventas")
U="Sergio (continuidad 036, Pedro Genta 19/10/2026)"
DOCS=[("0011-00083464",date(2026,6,23),Decimal("15329.04"),"20260623_PedroGenta_AjustePlazo.pdf"),
      ("0011-00085270",date(2026,7,22),Decimal("30665.61"),"20260722_PedroGenta_AjustePlazo.pdf")]
CERTS=[("0000-2026-270060",date(2026,6,23),Decimal("624825.58"),"retenciones_270060.pdf"),
       ("0000-2026-279534",date(2026,7,22),Decimal("625132.31"),"retenciones_279534.pdf")]

def main():
    _assert_target_is_wc()
    for _,_,_,n in DOCS:
        if not (ROOT/"04 2026 - 03 2027"/n).is_file(): raise RuntimeError("Falta ajuste PDF")
    for _,_,_,n in CERTS:
        if not (ROOT/"Retenciones 04 2026 - 03 2027"/n).is_file(): raise RuntimeError("Falta certificado PDF")
    print("Respaldo:",backup_verificado("pedro-genta-036"))
    for n,f,neto,archivo in DOCS:
        existente=fetch_all("SELECT IdVenta FROM dbo.[Venta Hacienda] WHERE IdConsignatario=? AND [Nro documento]=?",(320,n))
        if len(existente)>1: raise RuntimeError("Documento duplicado")
        if existente:
            vid=existente[0]["IdVenta"]
        else:
            cab={"idConsignatario":320,"idEstablecimiento":1,"idTipoDocumento":3,"numeroDocumento":n,"fecha":f,"alicuotaIVA":10.5,"documentoOriginal":str(ROOT/"04 2026 - 03 2027"/archivo)}
            linea={"idComprador":4657,"idTipoProducto":None,"cantidad":1,"unidadMedida":"Pesos","pesoTotal":0,"precioUnitarioA":neto,"precioUnitarioB":0}
            vid=ventas.create_venta(cab,[linea],[])
        ventas.agregar_documento_relacionado(2149,vid)
        print("Ajuste:",n,vid)
    st=[]
    for n,f,imp,archivo in CERTS:
        existente=fetch_all("SELECT Id,Importe FROM dbo.[Retenciones Ventas Hacienda] WHERE IdContacto=? AND [Nro Documento]=?",(320,n))
        if existente:
            if len(existente)!=1 or Decimal(str(existente[0]["Importe"]))!=imp: raise RuntimeError("Certificado diferente")
        else:
            st.append(("INSERT INTO dbo.[Retenciones Ventas Hacienda] (Id,Fecha,IdContacto,Documento,[Nro Documento],Importe,Imagen) SELECT (SELECT ISNULL(MAX(Id),0)+1 FROM dbo.[Retenciones Ventas Hacienda] WITH (UPDLOCK,HOLDLOCK)),?,320,'Cert. Retencion Ganancias',?,?,? WHERE NOT EXISTS (SELECT 1 FROM dbo.[Retenciones Ventas Hacienda] WITH (UPDLOCK,HOLDLOCK) WHERE IdContacto=320 AND [Nro Documento]=?)",(f,n,imp,str(ROOT/"Retenciones 04 2026 - 03 2027"/archivo),n)))
    original=fetch_all("SELECT [Gs Vs No Gravados] AS gasto FROM dbo.[Venta Hacienda] WHERE IdVenta=2149 AND IdConsignatario=320")[0]
    if Decimal(str(original["gasto"] or 0))==0:
        st.append(("UPDATE dbo.[Venta Hacienda] SET [Gs Vs No Gravados]=258.13 WHERE IdVenta=2149 AND IdConsignatario=320 AND ISNULL([Gs Vs No Gravados],0)=0",()))
    elif Decimal(str(original["gasto"]))!=Decimal("258.13"): raise RuntimeError("Redondeo original diferente")
    if st: execute_write_transaction(st)
    marcas=evidencia.leer_marcas(320)
    for n,_,_,_ in CERTS:
        rid=fetch_all("SELECT Id FROM dbo.[Retenciones Ventas Hacienda] WHERE IdContacto=? AND [Nro Documento]=?",(320,n))[0]["Id"]
        if ("ret.-ventas-hacienda",rid) not in marcas:
            evidencia.guardar_marca(320,"ret.-ventas-hacienda",rid,"venta-cargada",None,"pdf",f"Certificado {n}, cuota de liquidacion 0011-00082156 y ajuste financiero por plazo",U,"venta-hacienda",2149)
    print("Saldo:",fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS saldo FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?",(320,)))

if __name__=="__main__": main()
