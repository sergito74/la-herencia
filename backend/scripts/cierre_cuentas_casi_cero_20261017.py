"""036 — Cierre de las 10 cuentas casi en cero (decisiones de Sergio, 2026-10-17).

Uso (desde backend/):  python -m scripts.cierre_cuentas_casi_cero_20261017 [--aplicar]
Sin --aplicar solo muestra los saldos actuales. Con --aplicar: respaldo
verificado de WC y todas las correcciones en una transacción.

Decisiones:
- Bidcom (522): los $499,69 no fueron efectivo sino dinero disponible de Mercado Pago:
  se asigna el movimiento ML 6 a Bidcom y se borra el Pago efectivo 2254.
- Gregec (485): ajuste de cuenta corriente para cerrar en 0.
- Campo y Tecnología (493): +$6,92 prorrateado en los productos de la última factura (00005-00001313).
- Pérez Claudio (467): −$9,80 prorrateado en las labores de la factura 0002-669 (origen de la diferencia).
- GMRA (492): +$16,08 en la factura 00164-1644 (renglones de producto; la línea de compra particular no se toca).
- Edecan (176): +$89,29 prorrateado en la factura 6-3362.
- Sommier Center (578): +$105,98 en la factura 01134-608 (queda igual a lo cobrado por la Visa).
- FUNDEBO (41): −$199,15 en la factura 10-34772.
- YPF Debenedetti (282): percepciones $96,96 pagadas en efectivo por Sergio (ticket 07298-41965):
  Pago efectivo caja "Particular S" + devolución en la cuenta de socio de Sergio (patrón YPF Pilar).
- Cooperativa Eléctrica (23): facturas 0006-1526/1527 corregidas según PDF (Servicio Sepelio 1.674,50,
  IVA 1.280,80 → total 14.529,49 c/u) y ajuste por la factura anterior a 2011 que no está en el sistema.
"""

from __future__ import annotations

import sys

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all

USUARIO = "Sergio (036, cierre casi cero 2026-10-17)"
CUENTAS = {522: "Bidcom", 485: "Gregec", 493: "Campo y Tecnología", 467: "Pérez Claudio", 492: "GMRA",
           176: "Edecan", 578: "Sommier Center", 41: "FUNDEBO", 282: "YPF Debenedetti", 23: "Cooperativa"}

# (IdDeuda, delta del total en $, renglones excluidos del prorrateo)
PRORRATEOS = [
    (2143515004, 6.92, ()),          # Campo y Tecnología
    (2143515062, -9.80, ()),         # Pérez Claudio
    (2143513846, 16.08, ("Compra particular",)),  # GMRA
    (2143514980, 89.29, ()),         # Edecan
    (2143514907, 105.98, ("Redondeo",)),  # Sommier
    (2143515182, -199.15, ()),       # FUNDEBO
]


def saldo(cid: int) -> float:
    r = fetch_all("SELECT SUM(ISNULL(Credito,0)-ISNULL(Deuda,0)) s FROM dbo.vw_MovimientosCuenta_Base "
                  "WHERE IdContacto=? AND Fecha<='2026-09-30'", (cid,))
    return round(float(r[0]["s"] or 0), 2)


def prorratear(cur, id_deuda: int, delta: float, excluir: tuple[str, ...]) -> None:
    lineas = cur.execute("SELECT IdDetalleCompra, Cantidad, [Precio Unitario], IVA, [Producto/Servicio] "
                         "FROM dbo.Det_Compras WHERE IdCompra=?", id_deuda).fetchall()
    base = [l for l in lineas if not any(x.lower() in (l[4] or "").lower() for x in excluir)]
    bruto = sum(float(l[1]) * float(l[2]) * (1 + float(l[3] or 0) / 100) for l in base)
    if abs(bruto) < 0.01:
        raise RuntimeError(f"Factura {id_deuda}: sin renglones para prorratear")
    k = 1 + delta / bruto
    for l in base:
        cur.execute("UPDATE dbo.Det_Compras SET [Precio Unitario]=? WHERE IdDetalleCompra=?",
                    round(float(l[2]) * k, 4), l[0])


def aplicar() -> None:
    from src.features.vinculos.backup import backup_verificado

    print("Respaldo verificado:", backup_verificado("cierre-casi-cero-036"))
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        # Bidcom: Mercado Pago en vez de efectivo
        assert cur.execute("SELECT IdContacto FROM dbo.[Movimientos Mercado Libre] WHERE IdMovimiento=6 "
                           "AND Importe=-499.69").fetchone()[0] is None
        cur.execute("UPDATE dbo.[Movimientos Mercado Libre] SET IdContacto=522 WHERE IdMovimiento=6")
        cur.execute("DELETE FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=2254 AND IdContacto=522 "
                    "AND [Importe imputado]=499.69")
        assert cur.rowcount == 1
        # Gregec: cobro en efectivo redondeado $4 para arriba
        cur.execute("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto, Fecha, Lado, Importe, Motivo, Usuario) "
                    "VALUES (485, '2022-04-04', 'Credito', 4.00, ?, ?)",
                    "Venta 00003-00000009: el cobro en efectivo del 04/04/2022 ($105.130) se redondeó $4 sobre el "
                    "saldo de $105.126. Ajuste para cerrar la cuenta en 0 (decisión de Sergio).", USUARIO)
        # Prorrateos en facturas
        for id_deuda, delta, excluir in PRORRATEOS:
            prorratear(cur, id_deuda, delta, excluir)
        # Cooperativa: facturas según PDF
        for id_deuda in (2143515029, 2143515030):
            cur.execute("UPDATE dbo.Det_Compras SET [Precio Unitario]=1674.50 WHERE IdCompra=? "
                        "AND [Producto/Servicio]='Servicio Sepelio' AND [Precio Unitario]=1647.50", id_deuda)
            assert cur.rowcount == 1
            cur.execute("UPDATE dbo.Det_Compras SET IVA=? WHERE IdCompra=? AND [Producto/Servicio]='Grupo 5 Serv.Emergenc.'",
                        round(1280.80 / 10950.22 * 100, 6), id_deuda)
        cur.execute("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto, Fecha, Lado, Importe, Motivo, Usuario) "
                    "VALUES (23, '2011-01-31', 'Deuda', 267.00, ?, ?)",
                    "Saldo anterior al inicio del sistema: el pago BNA del 31/01/2011 ($268) cancela una factura de "
                    "2010 que no está cargada; con el redondeo de centavos de 2011-2026 deja $267 a favor. Ajuste para "
                    "cerrar en 0 (decisión de Sergio).", USUARIO)
        # YPF Debenedetti: percepciones pagadas en efectivo por Sergio
        cur.execute("INSERT INTO dbo.[Pagos efectivo] (IdContacto, IdTipoMovimiento, IdFormaPago, Fecha, Cuenta, Caja, "
                    "[Importe imputado]) VALUES (282, 1, 10, '2025-04-22', 'White', 'Particular S', 96.96)")
        cur.execute("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio, Tipo, Importe, Fecha, Medio, Motivo, Usuario, "
                    "Anulada, ImporteUSD, ImporteKgCarne) VALUES (1, 'Devolucion', 96.96, '2025-04-22', 'efectivo', ?, ?, 0, 0, 0)",
                    "Pago de percepciones del ticket YPF Debenedetti 07298-00041965 (efectivo $96,96) con fondos "
                    "propios de Sergio", USUARIO)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main(argv: list[str]) -> None:
    antes = {c: saldo(c) for c in CUENTAS}
    if "--aplicar" in argv:
        aplicar()
    for c, n in CUENTAS.items():
        print(f"{n:22} {antes[c]:>10,.2f} -> {saldo(c):>10,.2f}")


if __name__ == "__main__":
    main(sys.argv[1:])
