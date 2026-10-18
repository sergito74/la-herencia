"""036 — Cierre de Lartirigoyen (61), 18/10/2026.

Lartirigoyen (extranet y 70 resúmenes de cuenta corriente recibidos por mail 2019-2026) está en $0 / US$0 desde
jul-2024. Nuestra diferencia de +$179.793,32 se explica así (decisión de Sergio: corregir todo y cerrar en 0):
1. Conciliación tesorería 1432: el cheque propio 10215675 ($147.372,79) está ANULADO ("Anulado por 3619952"); se
   reemplazó por el cheque 3619952 ($146.936,85, BNA 03/05/2018) + la retención 0000-2017-000001 ($435,94), ya
   cargados. La conciliación masiva del 29/09/2026 lo tomó como pago → se borra.
2. Cheque 13826500 del 30/11/2010 ($11.966,45, "Lartirigoyen (Semilla y Fertilizante)"): paga una factura de 2010,
   anterior al inicio del sistema → ajuste Deuda (mismo criterio que Cooperativa Eléctrica).
3. FC 0149-00008895: Herbicida Heat son 5 frascos (PDF), estaba cargado 1,75 → total US$577,43.
4. FC 0149-00008903 estaba cargada como "8983".
5. Créditos de Lartirigoyen que no estaban: RR 0007-00001283 "Ing Rete" 22/12/2022 ($5.991,54) e IVA de la
   liquidación de maíz IC 3302-15602055 ($530,90, cobrado en la OP 0012-00188537 del 08/06/2020).
6. Redondeo final para dejar el saldo bimonetario en 0.
Idempotente.

Uso (desde backend/): python -m scripts.cierre_lartirigoyen_036
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C, USUARIO = 61, "Sergio (barrida 036)"
AJUSTES = [
    ("2010-11-30", "Deuda", 11966.45, "Saldo anterior al inicio del sistema: el cheque 13826500 del 30/11/2010 ($11.966,45, "
     "semilla y fertilizante) cancela una factura de 2010 que no está cargada."),
    ("2022-12-22", "Credito", 5991.54, "RR 0007-00001283 'Ing Rete' del 22/12/2022 ($5.991,54), crédito en la cuenta de "
     "Lartirigoyen aplicado en el AP 0149-00007888; no estaba cargado."),
    ("2020-06-08", "Credito", 530.90, "IVA de la liquidación de maíz IC 3302-15602055 ($530,90), pagado por Lartirigoyen en la "
     "OP 0012-00188537 junto con la LC ($10.047,70); solo estaba cargada la LC."),
]


def ejecutar(sentencias):
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        for sql, params in sentencias:
            cur.execute(sql, *params)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def saldo():
    bimonetaria.invalidar()
    r = bimonetaria.cargar_cuenta(C, refrescar=True)
    return r["saldoPesos"], r["saldoDolares"]


if __name__ == "__main__":
    _assert_target_is_wc()
    print("Antes:", saldo())
    print("Respaldo verificado:", backup_verificado("cierre-lartirigoyen-036"))
    s = [("DELETE FROM dbo.ConciliacionesTesoreria WHERE IdConciliacion = 1432 AND IdContacto = ? AND Medio = 'valores-propios' "
          "AND IdMovimiento = 1041", (C,)),
         ("UPDATE dbo.Det_Compras SET Cantidad = 5 WHERE IdCompra = 2143512990 AND [Producto/Servicio] = 'Kg. Heat' "
          "AND Cantidad = 1.75", ()),
         ("UPDATE dbo.Compras SET [Nro Documento] = '0149-00008903' WHERE IdDeuda = 2143513043 AND [Nro Documento] = '0149-00008983'", ())]
    for fecha, lado, importe, motivo in AJUSTES:
        if not fetch_all("SELECT 1 AS x FROM dbo.AjustesCuentaCorriente WHERE IdContacto = ? AND Fecha = ? AND Importe = ?",
                         (C, fecha, importe)):
            s.append(("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto, Fecha, Lado, Importe, Motivo, Usuario) "
                      "VALUES (?, ?, ?, ?, ?, ?)", (C, fecha, lado, importe, motivo + " (decisión de Sergio)", USUARIO)))
    ejecutar(s)
    pesos, dolares = saldo()
    print("Tras correcciones:", (pesos, dolares))
    if abs(pesos) >= 0.01:
        ejecutar([("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto, Fecha, Lado, Importe, Motivo, Usuario) VALUES (?, '2024-07-01', ?, ?, ?, ?)",
                   (C, "Deuda" if pesos > 0 else "Credito", round(abs(pesos), 2),
                    "Redondeo final: Lartirigoyen informa saldo $0 / US$0 (extranet y resúmenes 2024-2026); cierre en 0 "
                    "(decisión de Sergio).", USUARIO))])
    print("Final:", saldo())
