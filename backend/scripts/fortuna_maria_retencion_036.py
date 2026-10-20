"""036: retención recibida de Fortuna María, autorizada por Sergio 19/10/2026.

Certificado SICORE 0000-2025-000011, 27/11/2025, Ganancias,
factura 00003-00000017 ($7.704.060). Operación idempotente con respaldo.
Desde backend: python -m scripts.fortuna_maria_retencion_036
"""
from decimal import Decimal
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

PDF = Path(r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Ventas\04 2025 - 03 2026\Retencion Giamigli de Bolivar SA FC 17 el 27 11 20_261019_182919.pdf")
CERT = "0000-2025-000011"


def main():
    _assert_target_is_wc()
    if not PDF.is_file():
        raise RuntimeError("Falta el certificado PDF")
    existentes = fetch_all("SELECT Id, IdContacto, Fecha, Importe FROM dbo.[Retenciones Ventas Hacienda] WHERE [Nro Documento] = ? AND IdContacto = ?", (CERT, 630))
    if existentes:
        if len(existentes) != 1 or Decimal(str(existentes[0]["Importe"])) != Decimal("134960") or str(existentes[0]["Fecha"])[:10] != "2025-11-27":
            raise RuntimeError("Certificado existente con datos diferentes")
        print("Ya registrada:", existentes)
    else:
        movimientos = fetch_all("SELECT Deuda, Credito FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ?", (630,))
        saldo = sum((Decimal(str(r["Credito"])) - Decimal(str(r["Deuda"])) for r in movimientos), Decimal(0))
        if saldo != Decimal("134960"):
            raise RuntimeError(f"El saldo cambió: {saldo}")
        print("Respaldo verificado:", backup_verificado("fortuna-retencion-036"))
        execute_write_transaction([(
            "INSERT INTO dbo.[Retenciones Ventas Hacienda] (Id, Fecha, IdContacto, Documento, [Nro Documento], Importe, Imagen) "
            "SELECT (SELECT ISNULL(MAX(Id), 0)+1 FROM dbo.[Retenciones Ventas Hacienda] WITH (UPDLOCK, HOLDLOCK)), ?, ?, ?, ?, ?, ? "
            "WHERE NOT EXISTS (SELECT 1 FROM dbo.[Retenciones Ventas Hacienda] WITH (UPDLOCK, HOLDLOCK) WHERE IdContacto = ? AND [Nro Documento] = ?)",
            ("2025-11-27", 630, "Cert. Retencion Ganancias", CERT, Decimal("134960"), str(PDF), 630, CERT),
        )])
    print("Registro:", fetch_all("SELECT * FROM dbo.[Retenciones Ventas Hacienda] WHERE IdContacto = ? AND [Nro Documento] = ?", (630, CERT)))
    saldo = fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS saldo FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ?", (630,))[0]["saldo"]
    print("Saldo posterior:", saldo)
    if Decimal(str(saldo)) != 0:
        raise RuntimeError("La cuenta no quedó en cero; revisar sin agregar ajustes")
    from src.features.revision_cuentas import fichas
    usuario = "Sergio (036, retencion Fortuna Maria 19/10/2026)"
    fichas.confirmar_inventario(630, [
        {"tipo": "certificado", "disponible": True, "detalle": f"Ganancias {CERT}, 27/11/2025, $134.960; {PDF}"},
        {"tipo": "extracto", "disponible": True, "detalle": "Cobro Galicia 2939, eCheq 5885731, 10/12/2025, $7.569.100"},
    ], usuario)
    ficha = fichas.cambiar_estado(630, {"estado": "cerrada", "nota": "FC 00003-00000017 $7.704.060 = cobro Galicia $7.569.100 + retencion Ganancias 0000-2025-000011 $134.960. Certificado aportado y registro autorizado por Sergio el 19/10/2026. Saldo cero."}, usuario)
    print("Ficha:", ficha["estado"], "saldo:", ficha.get("saldoAlCorte"))


if __name__ == "__main__":
    main()
