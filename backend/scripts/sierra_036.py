"""036 — Marcelo Sierra (374), 18/10/2026: remuneraciones que faltaban según la planilla de liquidaciones y la caja.

Fuentes: "Personal/Remuneraciones modif..xlsx" (hoja "Liquidaciones Encargado": neto de recibo + "Total Bonificación" =
adicional fuera de recibo, por mes), "Cuentas a pagar/Cajas Giamigli.xlsx" (pagos "Adicional Sueldo Marcelo" y cuentas de
socios) y los recibos PDF (mandan sobre la planilla en el neto). Cada carga está respaldada por su pago:
- mar-2019 $8.330 (efectivo 01/04/2019), abr-2019 $7.350 (efectivo 02/05/2019), ene-2020 $11.360 (efectivo 01/02/2020),
  jul-2020 adicional $13.000 (estaba $12.960; pago efectivo 01/08/2020 $13.000); dic-2019: $90 pagados de más (redondeo).
- jun-2022: adicional $36.500 (efectivo 11/07/2022). El retroactivo de junio ($13.165 BNA 29/07 + $5.100 efectivo 01/08 =
  $18.265) ya estaba cargado como "julio 2022 (Retroactivo)".
- ago-2023: neto $235.797 en la planilla, recibo cargado $205.797 → $30.000 (BNA 05/09/2023); adicional $90.800 (caja 05/09/2023).
- feb-2026: adicional $359.700 (caja 10/03/2026). abr-2026: adicional $434.400 (caja 14/05/2026).
- dic-2025: el adicional ($624.200) lo pagaron los socios el 26/12/2025 (Sergio $324.200, Lucy $300.000) → se vinculan.
Idempotente.

Uso (desde backend/): python -m scripts.sierra_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

C = 374
ALTAS = [("2019-03-31", "Adicional fuera de recibo Marzo 2019", 8330.00),
         ("2019-04-30", "Adicional fuera de recibo Abril 2019", 7350.00),
         ("2020-01-31", "Adicional fuera de recibo Enero 2020", 11360.00),
         ("2022-06-30", "Adicional fuera de recibo Junio 2022", 36500.00),
         ("2023-08-31", "Complemento neto Agosto 2023 (pago BNA 05/09)", 30000.00),
         ("2023-08-31", "Adicional fuera de recibo Agosto 2023", 90800.00),
         ("2026-02-28", "Adicional fuera de recibo Febrero 2026", 359700.00),
         ("2026-04-30", "Adicional fuera de recibo Abril 2026", 434400.00)]
SOCIOS = [2225, 2722]

if __name__ == "__main__":
    _assert_target_is_wc()
    saldo = lambda: fetch_all("SELECT SUM(Credito - Deuda) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (C,))[0]["s"]
    print("Antes:", saldo())
    print("Respaldo verificado:", backup_verificado("sierra-036"))
    st = []
    for fecha, periodo, importe in ALTAS:
        if not fetch_all("SELECT 1 AS x FROM dbo.Remuneraciones WHERE IdContacto = ? AND [Periodo liquidado] = ?", (C, periodo)):
            st.append(("INSERT INTO dbo.Remuneraciones (IdContacto, [Fecha de pago], [Periodo liquidado], [Bonificacion adicional]) "
                       "VALUES (?, ?, ?, ?)", (C, fecha, periodo, importe)))
    for m in SOCIOS:
        if not fetch_all("SELECT 1 AS x FROM dbo.PagosSocioProveedor WHERE IdMovimientoSocio = ?", (m,)):
            st.append(("INSERT INTO dbo.PagosSocioProveedor (IdMovimientoSocio, IdContacto, Criterio, FechaAlta) "
                       "VALUES (?, ?, 'manual-036', SYSDATETIME())", (m, C)))
    st.append(("UPDATE dbo.Remuneraciones SET [Bonificacion adicional] = 13000 WHERE IdContacto = ? AND "
               "[Periodo liquidado] = 'Adicional fuera de recibo Julio 2020' AND [Bonificacion adicional] = 12960", (C,)))
    if not fetch_all("SELECT 1 AS x FROM dbo.AjustesCuentaCorriente WHERE IdContacto = ? AND Fecha = '2019-12-31'", (C,)):
        st.append(("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto, Fecha, Lado, Importe, Motivo, Usuario) VALUES (?, '2019-12-31', "
                   "'Deuda', 90, 'Redondeo: recibo diciembre 2019 $53.626, pagado $53.716 (BNA $38.716 + efectivo $15.000). Cierre en 0.', "
                   "'Sergio (barrida 036)')", (C,)))
    st.append(("UPDATE dbo.Remuneraciones SET [Bonificacion adicional] = 36500 WHERE IdContacto = ? AND "
               "[Periodo liquidado] = 'Adicional fuera de recibo Junio 2022' AND [Bonificacion adicional] = 54765", (C,)))
    execute_write_transaction(st)
    print("Después:", saldo())
