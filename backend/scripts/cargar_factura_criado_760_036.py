"""036 — Estudio Criado (115), 18/10/2026: factura que faltaba en WC y en Access.

Factura C 00003-00000760 de Criado Nicolás, 18/08/2025, $842.246,70 (honorarios de julio 2025, PDF en Dropbox
"Compras/04 2025 - 03 2026/20250818_NicolasCriado.pdf"). El pago Galicia del 18/08/2025 por el mismo importe ya
estaba en la cuenta sin factura. Se carga igual que la factura 00003-00000766 (centro de costos, rubro, campaña).
Idempotente.

Uso (desde backend/): python -m scripts.cargar_factura_criado_760_036
"""

from __future__ import annotations

from src.db.connection import execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

C, NRO, FECHA, IMPORTE, MODELO = 115, "00003-00000760", "2025-08-18", 842246.70, 2143515164
PDF = "04 2025 - 03 2026\20250818_NicolasCriado.pdf#04 2025 - 03 2026\20250818_NicolasCriado.pdf#"

if __name__ == "__main__":
    if fetch_all("SELECT 1 AS x FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", (C, NRO)):
        print("La factura ya está cargada.")
        raise SystemExit
    m = fetch_all("SELECT * FROM dbo.Det_Compras WHERE IdCompra = ?", (MODELO,))[0]
    print("Respaldo verificado:", backup_verificado("factura-criado-760-036"))
    r = execute_write_transaction([
        ("INSERT INTO dbo.Compras (Fecha, IdContacto, Tipo, [Tipo documento], [Nro Documento], Moneda, [Tipo de Cambio], "
         "[Ingresos Brutos], PercepcionIVA, [Conceptos no gravados], Guias, Comision, Financiacion, [Gastos Varios], "
         "[Ley de Sellos], [Res gral 4169/96], [Ajusta Tipo Cambio], [Documento Original]) OUTPUT INSERTED.IdDeuda "
         "VALUES (?, ?, 'C', 'Factura', ?, 'Pesos', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ?)", (FECHA, C, NRO, PDF)),
        lambda r: ("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, Unidad, [Producto/Servicio], IdFormulado, IdCentroCostos, "
                   "IdDestino, IdRubro, IdCampaña, [Campaña], [Precio Unitario], IVA, [Ajuste financiero]) "
                   "VALUES (?, 1, 'Unidades', 'Honorarios Julio 25', 0, ?, ?, ?, ?, ?, ?, 0, 0)",
                   (r[0], m["IdCentroCostos"], m["IdDestino"], m["IdRubro"], m["IdCampaña"], m["Campaña"], IMPORTE)),
    ])
    print("Factura cargada:", r[0])
    print(fetch_all("SELECT SUM(ISNULL(Credito,0)-ISNULL(Deuda,0)) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (C,)))
