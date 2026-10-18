"""036 — Marcelo Sierra (374), 18/10/2026: remuneraciones que faltaban según la planilla de liquidaciones y la caja.

Fuentes: "Personal/Remuneraciones modif..xlsx" (hoja "Liquidaciones Encargado": neto de recibo + "Total Bonificación" =
adicional fuera de recibo, por mes), "Cuentas a pagar/Cajas Giamigli.xlsx" (pagos "Adicional Sueldo Marcelo" y cuentas de
socios) y los recibos PDF (mandan sobre la planilla en el neto). Cada carga está respaldada por su pago:
- mar-2019 $8.330 (caja "Sueldo Marzo 2019" 01/04/2019); abr-2019 $7.350, ene-2020 $11.450, jul-2020 $13.000 (estaba $12.960):
  bonificación que Access tiene dentro del recibo y WC había perdido. Dic-2019 se pagaron $15.000 por $14.910 y ene-2020
  $11.360 por $11.450: se compensan.
- jun-2022: adicional $36.500 (efectivo 11/07/2022). El retroactivo de junio ($13.165 BNA 29/07 + $5.100 efectivo 01/08 =
  $18.265) ya estaba cargado como "julio 2022 (Retroactivo)".
- ago-2023: "Ajuste No Remunerativo" $30.000 (planilla; no está en el recibo PDF, neto $205.797; pagado aparte por BNA 05/09/2023);
  adicional $90.800 (Access y caja 05/09/2023).
- feb-2026: la planilla calcula $427.295 de adicional; la caja registra $359.700 pagados (dato a confirmar por Sergio).
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
         ("2020-01-31", "Adicional fuera de recibo Enero 2020", 11450.00),
         ("2022-06-30", "Adicional fuera de recibo Junio 2022", 36500.00),
         ("2023-08-31", "Ajuste No Remunerativo Agosto 2023", 30000.00),
         ("2023-08-31", "Adicional fuera de recibo Agosto 2023", 90800.00),
         ("2026-02-28", "Adicional fuera de recibo Febrero 2026", 359700.00),
         ("2026-04-30", "Adicional fuera de recibo Abril 2026", 434400.00)]
SOCIOS = [2225, 2722]

if __name__ == "__main__":
    _assert_target_is_wc()
    saldo = lambda: fetch_all("SELECT SUM(Credito - Deuda) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (C,))[0]["s"]
    print("Antes:", saldo())
    print("Respaldo verificado:", backup_verificado("sierra-036"))
    # el período de ago-2023 se cargó primero como "Complemento neto": se renombra antes de buscar las altas
    execute_write_transaction([("UPDATE dbo.Remuneraciones SET [Periodo liquidado] = 'Ajuste No Remunerativo Agosto 2023', "
                                "[Ajuste No Remunerativo] = 30000, [Bonificacion adicional] = NULL WHERE IdContacto = ? AND "
                                "[Periodo liquidado] = 'Complemento neto Agosto 2023 (pago BNA 05/09)'", (C,))])
    st = []
    for fecha, periodo, importe in ALTAS:
        if not fetch_all("SELECT 1 AS x FROM dbo.Remuneraciones WHERE IdContacto = ? AND [Periodo liquidado] = ?", (C, periodo)):
            campo = "[Ajuste No Remunerativo]" if periodo.startswith("Ajuste No Remunerativo") else "[Bonificacion adicional]"
            st.append((f"INSERT INTO dbo.Remuneraciones (IdContacto, [Fecha de pago], [Periodo liquidado], {campo}) "
                       "VALUES (?, ?, ?, ?)", (C, fecha, periodo, importe)))
    for m in SOCIOS:
        if not fetch_all("SELECT 1 AS x FROM dbo.PagosSocioProveedor WHERE IdMovimientoSocio = ?", (m,)):
            st.append(("INSERT INTO dbo.PagosSocioProveedor (IdMovimientoSocio, IdContacto, Criterio, FechaAlta) "
                       "VALUES (?, ?, 'manual-036', SYSDATETIME())", (m, C)))
    st.append(("UPDATE dbo.Remuneraciones SET [Bonificacion adicional] = 13000 WHERE IdContacto = ? AND "
               "[Periodo liquidado] = 'Adicional fuera de recibo Julio 2020' AND [Bonificacion adicional] = 12960", (C,)))
    # Revisión 18/10: ene-2020 es $11.450 según Access (estaba con el importe pagado, $11.360); los $90 que se pagaron de más
    # en dic-2019 ($15.000 por $14.910) se compensan con los $90 de menos de enero → sin ajuste.
    st.append(("UPDATE dbo.Remuneraciones SET [Bonificacion adicional] = 11450 WHERE IdContacto = ? AND "
               "[Periodo liquidado] = 'Adicional fuera de recibo Enero 2020' AND [Bonificacion adicional] = 11360", (C,)))
    st.append(("DELETE FROM dbo.AjustesCuentaCorriente WHERE IdContacto = ? AND Fecha = '2019-12-31' AND Importe = 90", (C,)))
    st.append(("UPDATE dbo.Remuneraciones SET [Bonificacion adicional] = 36500 WHERE IdContacto = ? AND "
               "[Periodo liquidado] = 'Adicional fuera de recibo Junio 2022' AND [Bonificacion adicional] = 54765", (C,)))
    execute_write_transaction(st)
    print("Después:", saldo())
