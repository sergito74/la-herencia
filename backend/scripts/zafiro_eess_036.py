"""036 — Electro Zafiro (402) y EESS Saladillo (30), 19/10/2026 (decisiones de Sergio).

1. Electro Zafiro FC 0006-31449 ($1.000, precintos, 07/10/2024): la pagó Sergio en efectivo con fondos propios → pago en
   efectivo (Caja 'Particular S') en la cuenta del proveedor + 'Devolucion' en la cuenta de socio de Sergio.
2. EESS Saladillo: desde 2025 los tickets se pagan con la App YPF (MERPAGO*APPYPFCOMB), que cobra menos que el ticket por
   el descuento de YPF. Una NC "Descuento App YPF" por ticket con la diferencia exacta ticket − cargo de la tarjeta,
   imputada al ticket. Se anula la aplicación automática 8188 (tarjeta 1619 sin vínculo, sobraba en el ticket 68681).
Idempotente.

Uso (desde backend/): python -m scripts.zafiro_eess_036
"""

from __future__ import annotations

import re

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

U = "Sergio (barrida 036)"
ZAFIRO, FC31449 = 402, 2143514824
EESS = 30
TICKETS = [2143514965, 2143514964, 2143515013, 2143515047, 2143515184, 2143515178, 2143515179]
CAB = "Fecha, IdContacto, Tipo, [Tipo documento], [Nro Documento], Moneda, [Tipo de Cambio], [Ingresos Brutos], PercepcionIVA, " \
      "[Conceptos no gravados], Guias, Comision, Financiacion, [Gastos Varios], [Ley de Sellos], [Res gral 4169/96], [Ajusta Tipo Cambio]"

if __name__ == "__main__":
    _assert_target_is_wc()
    print("Respaldo verificado:", backup_verificado("zafiro-eess-036"))
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM dbo.[Pagos efectivo] WHERE IdContacto = ? AND Fecha = '2024-10-07' AND [Importe imputado] = 1000", ZAFIRO)
        if not cur.fetchone():
            cur.execute("INSERT INTO dbo.[Pagos efectivo] (IdContacto, IdTipoMovimiento, IdFormaPago, Fecha, Cuenta, Caja, [Importe imputado]) "
                        "VALUES (?, 1, 3, '2024-10-07', 'White', 'Particular S', 1000)", ZAFIRO)
            cur.execute("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio, Tipo, Importe, Fecha, Medio, Motivo, Usuario, Anulada, ImporteUSD, ImporteKgCarne) "
                        "VALUES (1, 'Devolucion', 1000, '2024-10-07', 'efectivo', ?, ?, 0, 0, 0)",
                        "Pago de factura Electro Zafiro 0006-00031449 (efectivo $1.000) con fondos propios de Sergio", U)
        cur.execute("UPDATE dbo.AplicacionesPago SET Anulada = 1, MotivoAnulacion = 'Tarjeta 1619 sin vínculo: sobraba en el ticket (barrida 036)', "
                    "UsuarioAnulacion = ?, FechaAnulacion = SYSDATETIME() WHERE IdAplicacion = 8188 AND Anulada = 0", U)
        for t in TICKETS:
            cur.execute("SELECT c.Fecha, c.[Nro Documento], v.ImporteDocumento, (SELECT SUM(ImporteImputado) FROM dbo.Tarjetas_Resumenes_Lineas_Compras "
                        "WHERE IdCompra = c.IdDeuda) FROM dbo.Compras c JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda WHERE c.IdDeuda = ?", t)
            fecha, nro, total, tarjeta = cur.fetchone()
            nro_nc = "DESCAPP " + re.findall(r"\d+", nro)[-1].lstrip("0")
            dif = round(float(total) - float(tarjeta), 2)
            cur.execute("SELECT IdDeuda FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?", EESS, nro_nc)
            fila = cur.fetchone()
            if fila:
                nc = fila[0]
                cur.execute("DELETE FROM dbo.Det_Compras WHERE IdCompra = ?", nc)
            else:
                cur.execute(f"INSERT INTO dbo.Compras ({CAB}) OUTPUT INSERTED.IdDeuda VALUES (?, ?, 'A', 'Nota de Crédito', ?, 'Pesos', 1, "
                            "0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", fecha, EESS, nro_nc)
                nc = cur.fetchone()[0]
            cur.execute("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, [Producto/Servicio], IdFormulado, IdCentroCostos, IdDestino, IdRubro, "
                        "IdCampaña, [Campaña], [Precio Unitario], IVA, [Ajuste financiero]) SELECT TOP 1 ?, 1, ?, 0, IdCentroCostos, IdDestino, "
                        "IdRubro, IdCampaña, [Campaña], ?, 0, 0 FROM dbo.Det_Compras WHERE IdCompra = ? ORDER BY IdDetalleCompra",
                        nc, f"Descuento App YPF ticket {nro}"[:50], -dif, t)
            cur.execute("UPDATE dbo.AplicacionesPago SET Anulada = 1, MotivoAnulacion = 'Rehecha (barrida 036)', UsuarioAnulacion = ?, "
                        "FechaAnulacion = SYSDATETIME() WHERE OrigenMovimiento = 'comp-compra' AND IdMovimientoOrigen = ? AND Anulada = 0", U, nc)
            cur.execute("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, ImporteAplicado, "
                        "Fecha, Usuario, Anulada, Origen, NotaConciliacion) VALUES ('comp-compra', ?, 'CompraDeuda', ?, ?, SYSDATETIME(), ?, 0, 'manual', "
                        "'Barrida 036: descuento App YPF (ticket − cargo de la tarjeta)')", nc, t, dif, U)
            print(nro, "->", nro_nc, dif)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
