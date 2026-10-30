"""036, 30/10/2026: subsidios del Estado a la soja como ingreso de su campaña (decisión de Sergio del 26/10/2026),
cobrados de la Secretaría de Agricultura (5672) en el BNA, sin tocar a ningún comprador.

- 11/12/2020, BNA 15950, $134.391,10: Compensación y Estímulo Dec. 786/2020, campaña 2019/2020.
- 14/03/2016, BNA 15788, $1.323,00: Estímulo al Pequeño Productor (PEPP, Res. 126/2015 MECON), campaña 2015/2016.
Cada uno: una liquidación de soja de la Secretaría con 0 kg (no altera kilos ni precio) y el subsidio como bonificación;
el cobro del BNA la cancela. Se borran los dos movimientos que compensaban la cuenta sin documento: el cobro de caja
La Herencia 2493 ($134.391,10, de Access) y la NC X 2143524145 ($1.323, cargada el 26/10 sin script).
TC: BNA comprador divisa del día hábil anterior (regla de liquidaciones de granos).
Uso (desde backend/): python -m scripts.subsidios_soja_secretaria_036 [--aplicar]
"""
import json
import sys

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, fetch_one
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

SAGYP, CARGILL, FEDEA, SOJA = 5672, 258, 217, 8
SUBSIDIOS = [
    ("2020-12-11", "2019/2020", 134391.10, "SAF363 Dec. 786/2020", "Compensación soja Dec. 786/2020 (BNA 15950)"),
    ("2016-03-14", "2015/2016", 1323.00, "PEPP Res. 126/2015", "Estímulo PEPP Res. 126/2015 (BNA 15788)"),
]


def tc_anterior(fecha: str) -> float:
    return float(fetch_one("SELECT TOP 1 Comp_Divisa c FROM dbo.[Dolar BNA] WHERE Fecha < ? AND Comp_Divisa > 0 ORDER BY Fecha DESC",
                           (fecha,))["c"])


def resultado_soja() -> dict:
    return {r["c"]: round(float(r["b"] or 0), 2) for r in fetch_all(
        "SELECT Campaña c, SUM(BonifPesos) b FROM dbo.vw_ResultadosCultivo_Ventas WHERE Campaña IN ('2019/2020','2015/2016') "
        "GROUP BY Campaña", ())}


def caja_la_herencia() -> float:
    return round(float(fetch_one("SELECT SUM(CASE WHEN IdTipoMovimiento = 2 THEN [Importe imputado] ELSE -[Importe imputado] END) s "
                                 "FROM dbo.[Pagos efectivo] WHERE Caja = 'La Herencia'")["s"] or 0), 2)


def saldos() -> dict:
    bimonetaria.invalidar()
    return {c: (bimonetaria.cargar_cuenta(c, refrescar=True)["saldoPesos"], bimonetaria.cargar_cuenta(c)["saldoDolares"])
            for c in (SAGYP, CARGILL, FEDEA)}


if __name__ == "__main__":
    _assert_target_is_wc()
    assert fetch_one("SELECT 1 x FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo = 2493 AND IdContacto = ? AND ABS([Importe imputado] - 134391.10) < 0.005", (SAGYP,))
    assert fetch_one("SELECT 1 x FROM dbo.Compras WHERE IdDeuda = 2143524145 AND IdContacto = ?", (SAGYP,))
    antes = {"saldos": saldos(), "soja": resultado_soja(), "caja": caja_la_herencia()}
    print("antes", antes)
    if "--aplicar" not in sys.argv:
        raise SystemExit("Simulación: usar --aplicar para grabar.")
    respaldo = backup_verificado("subsidios-soja-secretaria-036")
    stmts = []
    for fecha, campania, importe, numero, concepto in SUBSIDIOS:
        tc = tc_anterior(fecha)
        stmts.append(("INSERT INTO dbo.[Venta Granos] (IdConsignatario, [Nro Documento], Fecha, [Precio unitario], [Tipo Cambio], IdProducto, "
                      "[Tipo de Grano], Campaña, Flete, Factor, [Cantidad entregada], [Cantidad vendida], AlicuotaIVA, [Retencion IVA], "
                      "[Ret IG], Percepciones, [Otra Retenciones]) VALUES (?, ?, ?, 0, ?, ?, 'Soja', ?, 0, 100, 0, 0, 0, 0, 0, 0, 0)",
                      (SAGYP, numero, fecha, tc, SOJA, campania)))
        stmts.append(("INSERT INTO dbo.[Venta Granos_Ajustes] (IdVenta, Concepto, Importe, AlicuotaIVA) "
                      "SELECT MAX(IdVenta), ?, ?, 0 FROM dbo.[Venta Granos] WHERE IdConsignatario = ? AND [Nro Documento] = ?",
                      (concepto, importe, SAGYP, numero)))
    stmts += [
        ("DELETE FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo = 2493 AND IdContacto = ?", (SAGYP,)),
        ("DELETE FROM dbo.Det_Compras WHERE IdCompra = 2143524145", ()),
        ("DELETE FROM dbo.[Vencimiento Compras] WHERE IdCompra = 2143524145", ()),
        ("DELETE FROM dbo.Compras WHERE IdDeuda = 2143524145 AND IdContacto = ?", (SAGYP,)),
        ("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
         "VALUES ('subsidios-soja-secretaria-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
         (json.dumps({"subsidios": SUBSIDIOS, "borrados": {"pagoEfectivo": 2493, "compra": 2143524145}}), respaldo,
          "Subsidios de soja como ingreso de su campaña: liquidación 0 kg de la Secretaría de Agricultura con bonificación, cobrada "
          "en el BNA. Borrados el cobro de caja 2493 y la NC X 2143524145 que compensaban la cuenta sin documento.")),
    ]
    execute_write_transaction(stmts)
    despues = {"saldos": saldos(), "soja": resultado_soja(), "caja": caja_la_herencia()}
    print("despues", despues)
