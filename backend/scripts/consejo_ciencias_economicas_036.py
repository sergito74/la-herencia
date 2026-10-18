"""036 — Consejo Ciencias Económicas de Olavarría (563), 18/10/2026.

Sergio: el pago Galicia 3458 del 24/09/2026 ($569.658,05) se transfirió a la cuenta de Ricardo Criado pero es el gasto
del Consejo por la emisión del balance 25-26; no hay ni habrá factura. Se reasigna al Consejo y se carga un comprobante
"SIN DOCUMENTO" por cada pago anual al Consejo (2024, 2025 y 2026, mismo concepto, ninguno tiene factura), con la
imputación de los honorarios del balance de Ricardo Criado (factura SIN DOCUMENTO 2143514791). Idempotente.

Uso (desde backend/): python -m scripts.consejo_ciencias_economicas_036
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all
from src.features.vinculos.backup import backup_verificado

C, MODELO, MOV = 563, 2143514791, 3458
GASTOS = [("2024-09-11", 371408.62, "Consejo - emisión balance 23-24"),
          ("2025-09-10", 424949.28, "Consejo - emisión balance 24-25"),
          ("2026-09-24", 569658.05, "Consejo - emisión balance 25-26")]

if __name__ == "__main__":
    _assert_target_is_wc()
    m = fetch_all("SELECT TOP 1 * FROM dbo.Det_Compras WHERE IdCompra = ?", (MODELO,))[0]
    print("Respaldo verificado:", backup_verificado("consejo-ciencias-economicas-036"))
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        cur.execute("UPDATE dbo.[Movimientos Galicia] SET IdContacto = ?, Contacto = 'Consejo Ciencias Economicas de Olavarria' "
                    "WHERE IdMovimiento = ? AND IdContacto = 210 AND [Débitos] = 569658.05", C, MOV)
        if cur.rowcount == 1:
            cur.execute("INSERT INTO dbo.ReasignacionesContacto (Origen, IdOrigen, IdContactoAnterior, IdContactoNuevo, Motivo, "
                        "Usuario, Fecha) VALUES ('Galicia', ?, 210, ?, ?, 'Sergio (barrida 036)', SYSDATETIME())", MOV, C,
                        "Gasto del Consejo por la emisión del balance 25-26, transferido a la cuenta de Ricardo Criado (Sergio 2026-10-18)")
        for fecha, importe, concepto in GASTOS:
            cur.execute("SELECT 1 FROM dbo.Compras WHERE IdContacto = ? AND Fecha = ? AND [Nro Documento] = 'SIN DOCUMENTO'", C, fecha)
            if cur.fetchone():
                continue
            cur.execute("INSERT INTO dbo.Compras (Fecha, IdContacto, Tipo, [Tipo documento], [Nro Documento], Moneda, [Tipo de Cambio], "
                        "[Ingresos Brutos], PercepcionIVA, [Conceptos no gravados], Guias, Comision, Financiacion, [Gastos Varios], "
                        "[Ley de Sellos], [Res gral 4169/96], [Ajusta Tipo Cambio]) OUTPUT INSERTED.IdDeuda "
                        "VALUES (?, ?, 'C', 'Factura', 'SIN DOCUMENTO', 'Pesos', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", fecha, C)
            id_compra = cur.fetchone()[0]
            cur.execute("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, Unidad, [Producto/Servicio], IdFormulado, IdCentroCostos, "
                        "IdDestino, IdRubro, IdCampaña, [Campaña], [Precio Unitario], IVA, [Ajuste financiero]) "
                        "VALUES (?, 1, 'Unidades', ?, 0, ?, ?, ?, ?, ?, ?, 0, 0)", id_compra, concepto, m["IdCentroCostos"],
                        m["IdDestino"], m["IdRubro"], m["IdCampaña"], m["Campaña"], importe)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    for c in (C, 210):
        print(c, fetch_all("SELECT SUM(ISNULL(Credito,0)-ISNULL(Deuda,0)) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (c,)))
