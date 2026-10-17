"""036 — Cierre de Armando Oscar Mori (376), 17/10/2026 (personal auxiliar eventual).

Según la Planilla de trabajos eventuales:
- Jornal del 27/03/2025 (vacunación y ecografías, $63.500, pagado por Galicia el 31/03/2025): faltaba la remuneración →
  se carga con la misma composición que el jornal de abril 2025 (escalada a $63.500 netos).
- Jornal del 10/06/2025 (encierre venta de terneros, $65.600): el pago Galicia 2628 del 23/06/2025 "Armando Oscar Mori"
  estaba asignado al contacto Banco Galicia (518) → se reasigna a Mori.

Uso (desde backend/): python -m scripts.cierre_mori_20261017
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all
from src.features.vinculos.backup import backup_verificado

C, MODELO, NETO = 376, 1829633227, 63500.00
SUMAN = ("Sueldo basico", "Adic futuros aumentos", "Vacaciones", "Ajuste No Remunerativo", "Aguinaldo", "Bonificacion adicional")
RESTAN = ("Jubilacion", "Servicio de Sepelio")

if __name__ == "__main__":
    m = fetch_all("SELECT * FROM dbo.Remuneraciones WHERE IdSalario = ?", (MODELO,))[0]
    neto_modelo = sum(float(m[c] or 0) for c in SUMAN) - sum(float(m[c] or 0) for c in RESTAN)
    k = NETO / neto_modelo
    valores = {c: round(float(m[c] or 0) * k, 2) for c in SUMAN + RESTAN}
    redondeo = round(NETO - (sum(valores[c] for c in SUMAN) - sum(valores[c] for c in RESTAN)), 2)
    print("Respaldo verificado:", backup_verificado("cierre-mori-036"))
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        cols = ", ".join(f"[{c}]" for c in SUMAN + RESTAN)
        cur.execute(f"INSERT INTO dbo.Remuneraciones (IdContacto, [Fecha de pago], [Periodo liquidado], {cols}, Redondeo) "
                    f"VALUES (?, '2025-03-27', 'Jornal 27/3 (vacunación y ecografías)', {', '.join('?' * len(SUMAN + RESTAN))}, ?)",
                    C, *[valores[c] for c in SUMAN + RESTAN], redondeo)
        cur.execute("UPDATE dbo.[Movimientos Galicia] SET IdContacto = ?, Contacto = 'Armando Oscar Mori' "
                    "WHERE IdMovimiento = 2628 AND IdContacto = 518 AND [Débitos] = 65600", C)
        assert cur.rowcount == 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(fetch_all("SELECT SUM(ISNULL(Credito,0)-ISNULL(Deuda,0)) s FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ?", (C,)))
