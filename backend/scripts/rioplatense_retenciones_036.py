"""036: certificados Rioplatense y cierre autorizado por Sergio 19/10/2026."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from src.db.connection import fetch_all, execute_write_transaction, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado
from src.features.revision_cuentas import fichas, evidencia

U = "Sergio (036, Rioplatense 19/10/2026)"
DIR = Path(r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Ventas\04 2024 - 03 2025\Retenciones")
CERTS = [("0001-10074236","Cert. Retencion Ganancias",Decimal("799029.20"),DIR/"ATT27391PDF_261019_191058_Ganancias.pdf"),
         ("0001-20082385","Cert. Retencion IIBB",Decimal("301315.95"),DIR/"ATT27391PDF_261019_191058_Ingresos_Brutos.pdf")]
NOTA = "Sergio autoriza cierre sin resumen de cuenta. Venta 00003-00000015 $44.393.883,30 = eCheq 40947 $43.293.538,15 + Ganancias $799.029,20 + IIBB $301.315,95. Certificados 06/01/2025 en Dropbox."


def main():
    _assert_target_is_wc()
    st=[]
    for numero,tipo,importe,pdf in CERTS:
        if not pdf.is_file():
            raise RuntimeError(f"Falta {pdf}")
        existe=fetch_all("SELECT Id,Fecha,Importe,Documento FROM dbo.[Retenciones Ventas Hacienda] WHERE IdContacto = ? AND [Nro Documento] = ?",(586,numero))
        if existe:
            if len(existe)!=1 or Decimal(str(existe[0]["Importe"]))!=importe or str(existe[0]["Fecha"])[:10]!="2025-01-06" or existe[0]["Documento"]!=tipo:
                raise RuntimeError("Certificado existente diferente")
        else:
            st.append(("INSERT INTO dbo.[Retenciones Ventas Hacienda] (Id,Fecha,IdContacto,Documento,[Nro Documento],Importe,Imagen) SELECT (SELECT ISNULL(MAX(Id),0)+1 FROM dbo.[Retenciones Ventas Hacienda] WITH (UPDLOCK,HOLDLOCK)),?,?,?,?,?,? WHERE NOT EXISTS (SELECT 1 FROM dbo.[Retenciones Ventas Hacienda] WITH (UPDLOCK,HOLDLOCK) WHERE IdContacto = ? AND [Nro Documento] = ?)",("2025-01-06",586,tipo,numero,importe,str(pdf),586,numero)))
    mov=fetch_all("SELECT IdContacto,[Débitos] AS importe,Concepto FROM dbo.[Movimientos Galicia] WHERE IdMovimiento = ?",(2354,))[0]
    if mov["IdContacto"]==586:
        if Decimal(str(mov["importe"]))!=Decimal("5861.32") or mov["Concepto"]!="907173 - ING. BRUTOS S/ CRED":
            raise RuntimeError("Cargo bancario diferente")
        if fetch_all("SELECT Estado FROM dbo.RevisionFichas WHERE IdContacto = ? AND Estado IN ('cerrada','cerrada-con-excepcion')",(12,)):
            raise RuntimeError("ARBA cerrada: detener reasignacion")
        st.extend([
            ("INSERT INTO dbo.ReasignacionesContacto (Origen,IdOrigen,IdContactoAnterior,IdContactoNuevo,Motivo,Usuario,Fecha) SELECT 'Galicia',2354,586,12,?,?,SYSDATETIME() FROM dbo.[Movimientos Galicia] WITH (UPDLOCK,HOLDLOCK) WHERE IdMovimiento=2354 AND IdContacto=586 AND [Débitos]=5861.32",("IIBB sobre creditos LEY 12837-BS.AS., impuesto bancario ARBA; mismo concepto que los restantes cargos asignados a ARBA. No es deuda del frigorifico.",U)),
            ("UPDATE dbo.[Movimientos Galicia] SET IdContacto=12,Contacto='ARBA' WHERE IdMovimiento=2354 AND IdContacto=586 AND [Débitos]=5861.32",()),
        ])
    elif mov["IdContacto"]!=12:
        raise RuntimeError("Cargo asignado a otra cuenta")
    if st:
        print("Respaldo verificado:",backup_verificado("rioplatense-retenciones-036"))
        execute_write_transaction(st)
    saldo=Decimal(str(fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS s FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ?",(586,))[0]["s"])).quantize(Decimal("0.01"))
    print("Saldo:",saldo)
    if saldo!=0:
        raise RuntimeError("No cierra: revisar sin crear ajustes")
    corte=date(2026,9,30)
    marcas=evidencia.leer_marcas(586)
    for numero,_,_,_ in CERTS:
        registro=fetch_all("SELECT Id FROM dbo.[Retenciones Ventas Hacienda] WHERE IdContacto=? AND [Nro Documento]=?",(586,numero))[0]
        if ("ret.-ventas-hacienda",registro["Id"]) not in marcas:
            evidencia.guardar_marca(586,"ret.-ventas-hacienda",registro["Id"],"venta-cargada",None,"pdf",f"Certificado {numero} correspondiente a venta 00003-00000015",U,"venta-hacienda",133)
    if not fetch_all("SELECT IdSaldoExterno FROM dbo.RevisionSaldosExternos WHERE IdContacto = ? AND Fuente='sin-estado' AND Anulado=0 AND Nota=?",(586,NOTA)):
        evidencia.crear_saldo_externo(586,corte,0,"Pesos","sin-estado",str(DIR),NOTA,U)
    fichas.confirmar_inventario(586,[
        {"tipo":"certificado","disponible":True,"detalle":"Ganancias 0001-10074236 e IIBB 0001-20082385, ambos del 06/01/2025, PDFs vinculados"},
        {"tipo":"dropbox","disponible":True,"detalle":"Liquidacion de venta 17/12/2024 00003-00000015"},
        {"tipo":"extracto","disponible":True,"detalle":"Galicia 2349: cobro eCheq 40947, 17/01/2025, $43.293.538,15"},
        {"tipo":"estado-proveedor","disponible":False,"detalle":"Sergio informa que no hay resumen de cuenta y autoriza cierre"},
    ],U)
    ficha=fichas.cambiar_estado(586,{"estado":"cerrada","nota":NOTA},U)
    print("Ficha:",ficha["estado"],ficha.get("saldoAlCorte"))
    print("Retenciones:",fetch_all("SELECT Id,Fecha,[Nro Documento],Importe FROM dbo.[Retenciones Ventas Hacienda] WHERE IdContacto=?",(586,)))


if __name__ == "__main__":
    main()
