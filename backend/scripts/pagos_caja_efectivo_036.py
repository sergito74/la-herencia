"""036 — Pagos en efectivo de "Cajas Giamigli.xlsx" que faltaban en las cuentas de proveedores (19/10/2026, pedido de Sergio).

Cruce de la planilla (hojas "Caja Efectivo Pesos" y "Caja chica campo") contra las compras: cada egreso con número de
boleta/factura (o proveedor e importe el mismo día) cuya compra no tenía pago en la cuenta. Se carga un pago en efectivo
(Caja de la planilla, forma Efectivo) imputado a esa compra y se vincula el movimiento de caja al contacto.
Además se agregan a MovimientosCajaEfectivo las filas de la planilla posteriores a la migración 027 (sep/oct 2026).
Extragas 2017-2018 (cuenta ya cerrada) no se toca. Idempotente.

Uso (desde backend/): python -m scripts.pagos_caja_efectivo_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

U = "Sergio (barrida 036, cajas)"
# (caja, fecha, importe, IdContacto, IdDeuda, concepto de la planilla)
PAGOS = [
    ("CampoChica", "2024-10-05", 22000, 560, 2143514827, "Boleta 0011-00000126"),
    ("CampoChica", "2024-10-30", 22000, 560, 2143514872, "Boleta 0011-00000126"),   # la boleta es la 129 (la planilla repite 126)
    ("CampoChica", "2024-11-12", 22000, 560, 2143514926, "Boleta 0011-00000130"),
    ("CampoChica", "2024-12-17", 27000, 560, 2143514927, "Boleta 0011-00000131"),
    ("CampoChica", "2025-01-14", 31000, 560, 2143514970, "Boleta 0011-00000134"),
    ("CampoChica", "2025-06-20", 33000, 560, 2143515109, "Boleta 0011-000000196"),
    ("CampoChica", "2025-07-10", 33000, 560, 2143515274, "Boleta 0011-000000195"),
    ("CampoChica", "2025-09-22", 33000, 560, 2143515273, "Boleta 0011-000000197"),
    ("CampoChica", "2025-11-01", 33000, 560, 2143515275, "Boleta 0011-000000198"),
    ("CampoChica", "2026-02-12", 16500, 560, 2143515400, "Boleta 0011-000000138"),
    ("CampoChica", "2026-03-20", 18000, 560, 2143517407, "Boleta 0011-00000140"),
    ("CampoChica", "2026-05-09", 25000, 560, 2143521581, "Boleta 0001-00013882"),
    ("CampoChica", "2026-06-21", 56000, 560, 2143518487, "Boleta 0011-00000072"),
    ("CampoChica", "2026-07-04", 28000, 560, 2143518488, "Boleta 0011-00000092"),
    ("CampoChica", "2026-10-01", 58000, 560, 2143522648, "Boleta 0011-00000144"),
    ("CampoChica", "2022-03-25", 2130, 97, 2143513592, "Boleta 0011-00000180"),
    ("CampoChica", "2025-02-02", 31000, 97, 2143514969, "Boleta 20052"),
    ("CampoChica", "2025-02-16", 13000, 97, 2143515016, "Factura 1536"),
    ("CampoChica", "2025-03-14", 33000, 97, 2143515018, "Boleta 20053"),
    ("CampoChica", "2025-04-18", 33000, 97, 2143515052, "Boleta 59798"),
    ("CampoChica", "2025-05-20", 33000, 97, 2143515108, "Boleta 059799"),
    ("CampoChica", "2026-08-15", 56000, 97, 2143519518, "Boleta 0059799"),
    ("CampoChica", "2026-09-03", 14499, 249, 2143522643, "Supermercado Actual"),
    ("CampoChica", "2026-09-03", 9000, 80, 2143522642, "Palomino e hijos"),
]
# Filas nuevas de la planilla (posteriores a la migración 027 o que no habían entrado)
CAJA_NUEVAS = [
    ("GiamigliSA", "2014-08-06", -195.01, "Jauregui y Morales", None, 48),
    ("GiamigliSA", "2026-10-02", -508000, "Adicional Sueldo Marcelo Septiembre 26", None, 374),
    ("GiamigliSA", "2026-10-15", -100000, "Caja Chica Campo", None, None),
    ("GiamigliSA", "2026-10-15", -30000, "Aporte escombro camino", None, None),
    ("CampoChica", "2026-09-03", -14499, "Supermercado Actual", "10 Vinagre", 249),
    ("CampoChica", "2026-09-03", -9000, "Palomino e hijos", "1 Bolsa Cemento", 80),
    ("CampoChica", "2026-10-01", -58000, "Boleta 0011-00000144", "2 Garrafas", 560),
    ("CampoChica", "2026-10-15", 100000, "Aporte Efectivo", None, None),
]

if __name__ == "__main__":
    _assert_target_is_wc()
    print("Respaldo verificado:", backup_verificado("pagos-caja-efectivo-036"))
    st = []
    for caja, fecha, importe, concepto, detalle, contacto in CAJA_NUEVAS:
        if not fetch_all("SELECT 1 x FROM dbo.MovimientosCajaEfectivo WHERE Caja = ? AND Fecha = ? AND ABS(Importe - ?) <= 0.01", (caja, fecha, importe)):
            st.append(("INSERT INTO dbo.MovimientosCajaEfectivo (Caja, Fecha, Concepto, Detalle, Importe, Cuenta, FormaPago, IdContactoRelacionado, Usuario) "
                       "VALUES (?, ?, ?, ?, ?, ?, 'Efectivo', ?, ?)", (caja, fecha, concepto, detalle, importe, "B" if caja == "GiamigliSA" else None, contacto, U)))
    nuevos = 0
    for caja, fecha, importe, contacto, deuda, concepto in PAGOS:
        if fetch_all("SELECT 1 x FROM dbo.[Pagos efectivo] WHERE IdContacto = ? AND Fecha = ? AND ABS([Importe imputado] - ?) <= 0.01", (contacto, fecha, importe)):
            continue
        nuevos += 1
        st.append(("INSERT INTO dbo.[Pagos efectivo] (IdContacto, IdTipoMovimiento, IdFormaPago, Fecha, Cuenta, Caja, [Importe imputado]) "
                   "VALUES (?, 1, 3, ?, 'White', ?, ?)", (contacto, fecha, caja, importe)))
        st.append(("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, ImporteAplicado, Fecha, "
                   "Usuario, Anulada, Origen, NotaConciliacion) SELECT 'efectivo', MAX(IdPagoEfectivo), 'CompraDeuda', ?, ?, SYSDATETIME(), ?, 0, 'manual', ? "
                   "FROM dbo.[Pagos efectivo] WHERE IdContacto = ? AND Fecha = ? AND ABS([Importe imputado] - ?) <= 0.01",
                   (deuda, importe, U, f"Cajas Giamigli.xlsx: {concepto}", contacto, fecha, importe)))
        st.append(("UPDATE dbo.MovimientosCajaEfectivo SET IdContactoRelacionado = ? WHERE Caja = ? AND Fecha = ? AND ABS(Importe + ?) <= 0.01 "
                   "AND IdContactoRelacionado IS NULL", (contacto, caja, fecha, importe)))
    if st:
        execute_write_transaction(st)
    print("Pagos en efectivo nuevos:", nuevos)
