"""Cierre Wallace autorizado por Sergio 19/10/2026, sin resumen actualizado."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from src.db.connection import fetch_all, execute_write_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.revision_cuentas import fichas, evidencia

USUARIO = "Sergio (036, cierre Wallace 19/10/2026)"
PDF = Path(r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Ventas\04 2024 - 03 2025\20240611_Wallace.pdf")
MOTIVO = "Redondeo Wallace: liquidacion 24837 + bonificacion 1355 menos cobro Galicia 2656. Cierre en cero autorizado por Sergio el 19/10/2026, sin resumen actualizado."


def main():
    if not PDF.is_file():
        raise RuntimeError("Falta PDF")
    saldo = Decimal(str(fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS s FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ?", (600,))[0]["s"])).quantize(Decimal("0.0001"))
    if saldo not in (Decimal("0"), Decimal("0.0219")):
        raise RuntimeError(f"Saldo inesperado: {saldo}")
    print("Respaldo:", backup_verificado("cierre-wallace-036"))
    st = [("UPDATE dbo.[Venta Hacienda] SET [Documento Original] = ? WHERE IdVenta = ? AND IdConsignatario = ? AND ([Documento Original] IS NULL OR [Documento Original] = '')", (str(PDF),137,600))]
    if saldo:
        st.append(("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario) SELECT ?,?,'Deuda',?,?,? WHERE NOT EXISTS (SELECT 1 FROM dbo.AjustesCuentaCorriente WITH (UPDLOCK,HOLDLOCK) WHERE IdContacto = ? AND Motivo = ?)", (600,"2025-07-10",saldo,MOTIVO,USUARIO,600,MOTIVO)))
    execute_write_transaction(st)
    corte = date(2026,9,30)
    if not fetch_all("SELECT IdSaldoExterno FROM dbo.RevisionSaldosExternos WHERE IdContacto = ? AND Fuente = 'sin-estado' AND Anulado = 0 AND Nota = ?", (600,MOTIVO)):
        evidencia.crear_saldo_externo(600,corte,0.0,"Pesos","sin-estado",str(PDF),MOTIVO,USUARIO)
    fichas.confirmar_inventario(600,[
        {"tipo":"dropbox","disponible":True,"detalle":"Liquidacion 24837 y NC bonificacion 1355, PDFs en Ventas"},
        {"tipo":"extracto","disponible":True,"detalle":"Galicia 2656, 10/07/2025, $1.833.341,86, Wallace CUIT 30692071898"},
        {"tipo":"estado-proveedor","disponible":False,"detalle":"Sergio informa que no tiene resumen actualizado; autoriza cierre en cero"},
    ],USUARIO)
    f=fichas.cambiar_estado(600,{"estado":"cerrada","nota":MOTIVO},USUARIO)
    print("Ficha:",f["estado"],"Saldo:",f.get("saldoAlCorte"))
    print("Saldo actual:",fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS saldo FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ?",(600,)))


if __name__ == "__main__":
    main()
