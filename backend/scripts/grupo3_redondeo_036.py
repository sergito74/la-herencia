"""036 — grupo 3 (cuentas chicas): redondeo de facturas a lo pagado cuando la diferencia es ≤0,10%.

Regla aprobada por Sergio el 29/10/2026 (estrategia-imputaciones-20261029.md, punto 4): los centavos no se cancelan con
pagos; se redondea la factura. En orden de vencimiento, a cada factura se le quitan el resto abierto y los centavos que
le pone otro pago (aplicación <0,10% de la factura), y se recalcula el FIFO antes de pasar a la siguiente. No cuentan
como centavos los asientos que son en sí mismos un ajuste chico (p. ej. "La Herencia" $0,08 de 2011). Se graba solo
en las cuentas que quedan en $0 y sin aplicaciones de centavos; el resto va a excepciones. Solo facturas en pesos sin
cuotas. Método de `grupo2_redondeo_tarjeta_036`: escalar los precios de los renglones o ajustar "Gastos Varios".
Uso (desde backend/): python -m scripts.grupo3_redondeo_036 [--aplicar]
"""

from __future__ import annotations

import json
import sys
from datetime import date

from scripts.grupo3_diagnostico_036 import LIMITE, cuentas
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.recalculo_fifo import cambio, entrada, motor
from src.features.vinculos.backup import backup_verificado


def _facturas(items: list[dict]) -> list[dict]:
    return sorted((i for i in items if i["clave"][0] == "Compras" and i["lado"] == "D" and i["clase"] == "doc"
                   and i["moneda"] == "ARS" and i["clave"][2] is None and i["importe"] > 0), key=motor._orden)


def _centavos(res: dict, fac: dict, tamanos: dict) -> float:
    """Centavos que otro pago pone en la factura, sin contar asientos que ya son un ajuste chico."""
    return sum(float(a["importeArs"]) for a in res["aplicaciones"]
               if tuple(a["debito"])[:2] == tuple(fac["clave"])[:2] and float(a["importeArs"]) < fac["importe"] * LIMITE
               and tamanos.get(tuple(a["credito"])[:2], 0) >= fac["importe"] * LIMITE)


def simular(e: dict, tc, hoy: date) -> tuple[dict, dict]:
    """{clave: (total, nuevo)} y el resultado final del FIFO."""
    items = [dict(i) for i in e["items"]]
    tamanos = {tuple(i["clave"])[:2]: float(i["importe"]) for i in items}
    cambios = {}
    probadas = set()
    for _ in range(50):
        res = motor.recalcular(items, e["fijos"], tc, hoy)
        por_clave = {tuple(i["clave"])[:2]: i for i in res["items"]}
        for fac in _facturas(items):
            clave = tuple(fac["clave"])[:2]
            quitar = float(por_clave[clave]["rem"]) + _centavos(res, fac, tamanos)
            if clave in probadas or not 0.005 <= quitar <= fac["importe"] * LIMITE:
                continue
            probadas.add(clave)
            # Solo si acerca el saldo abierto a cero: si no, los centavos son de otro comprobante.
            if abs(_abierto(items) - quitar) >= abs(_abierto(items)) - 0.001:
                continue
            cambios.setdefault(clave, [round(fac["importe"], 2), None])
            fac["importe"] = round(fac["importe"] - quitar, 2)
            cambios[clave][1] = fac["importe"]
            break
        else:
            return {k: v for k, v in cambios.items() if abs(v[1] - v[0]) >= 0.005}, res
    return {k: v for k, v in cambios.items() if abs(v[1] - v[0]) >= 0.005}, res


def _abierto(items: list[dict]) -> float:
    """Facturado menos pagado de la cuenta (lo que quedaría abierto con un FIFO perfecto)."""
    return sum(float(i["importe"]) * (1 if i["lado"] == "D" else -1) for i in items if i["moneda"] == "ARS")


def casos() -> tuple[list[dict], list[dict]]:
    hoy = date.today()
    tc = cambio.funcion_tc(hoy)
    aplicar, excepciones = [], []
    for ct, e in entrada.armar(cuentas()).items():
        if not e["items"]:
            continue
        cambios, res = simular(e, tc, hoy)
        if not cambios:
            continue
        tamanos = {tuple(i["clave"])[:2]: float(i["importe"]) for i in res["items"]}
        abierto = sum(float(i["rem"]) * (1 if i["lado"] == "D" else -1) for i in res["items"])
        quedan = [f for f in _facturas(res["items"]) if _centavos(res, f, tamanos) >= 0.01]
        fila = {"ct": ct, "nombre": e["nombre"], "abierto": round(abierto, 2),
                "cambios": {k[1]: v for k, v in cambios.items()}}
        (aplicar if abs(abierto) < 0.005 and not quedan else excepciones).append(fila)
    return aplicar, excepciones


if __name__ == "__main__":
    _assert_target_is_wc()
    aplicar, excepciones = casos()
    n = sum(len(c["cambios"]) for c in aplicar)
    print(len(aplicar), "cuentas,", n, "facturas a redondear; ajuste total",
          round(sum(v[1] - v[0] for c in aplicar for v in c["cambios"].values()), 2))
    for c in excepciones:
        print("  excepción:", c["ct"], c["nombre"], "queda abierto", c["abierto"], c["cambios"])
    if "--aplicar" not in sys.argv or not aplicar:
        raise SystemExit("Simulación: usar --aplicar para grabar." if aplicar else "Nada pendiente.")
    ids = [i for c in aplicar for i in c["cambios"]]
    totales = {r["i"]: r for r in fetch_all(
        f"SELECT IdDeuda AS i, GranTotal AS g, TotalDetalleCompra AS d FROM dbo.vw_Cns_Total_Compra WHERE IdDeuda IN ({','.join(map(str, ids))})", ())}
    respaldo = backup_verificado("grupo3-redondeo-036")
    stmts = []
    for c in aplicar:
        for i, (total, nuevo) in c["cambios"].items():
            g, d = float(totales[i]["g"]), float(totales[i]["d"] or 0)
            if abs(d) > 1e-6:
                stmts.append(("UPDATE dbo.Det_Compras SET [Precio Unitario] = [Precio Unitario] * ? WHERE IdCompra = ?",
                              ((nuevo - (g - d)) / d, i)))
            else:
                stmts.append(("UPDATE dbo.Compras SET [Gastos Varios] = ISNULL([Gastos Varios], 0) + ? WHERE IdDeuda = ?",
                              (nuevo - total, i)))
    stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES ('grupo3-redondeo-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
                  (json.dumps({str(i): v for c in aplicar for i, v in c["cambios"].items()}), respaldo,
                   f"{n} facturas de {len(aplicar)} cuentas chicas redondeadas a lo pagado (≤0,10%, regla 29/10/2026).")))
    execute_write_transaction(stmts)
    print("Aplicado. Respaldo:", respaldo)
