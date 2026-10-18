"""036 — Lartirigoyen (61), 18/10/2026: valuación en dólares de los movimientos en pesos (tabla ValuacionProveedor).

Sergio: la cuenta tiene que cerrar en cero en pesos Y en dólares. Lartirigoyen lleva dos subcuentas (resúmenes 2018-2026):
- las facturas/ND/NC en dólares van a la subcuenta en dólares;
- los documentos en pesos (ND por diferencia de cambio o intereses, facturas de gastos en pesos, los pagos que
  Lartirigoyen nos hizo) quedan en la subcuenta en pesos;
- cada pago o crédito en pesos (transferencias, cheques, tarjeta, liquidaciones de granos, retenciones) cancela
  primero lo que se debe en pesos y el resto se aplica ("Aplica saldo" / "Aplicación pago en especie" / AP) a las
  facturas en dólares pendientes, en orden, al tipo de cambio de cada factura; la diferencia con el dólar del día la
  cobra Lartirigoyen aparte con una ND por diferencia de cambio en pesos.
Este script reproduce esa aplicación y graba, por cada fila en pesos, los dólares que movió en el libro de
Lartirigoyen (0 para los documentos en pesos). Reemplaza la valuación anterior de la cuenta. Idempotente.

Uso (desde backend/): python -m scripts.valuacion_lartirigoyen_036
"""

from __future__ import annotations

from collections import defaultdict

from src.db.connection import _assert_target_is_wc, execute_write_transaction
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C = 61
FUENTE = "Aplicación de Lartirigoyen: pesos al TC de la factura en dólares que cancela (resúmenes 2018-2026, Sergio 18/10/2026)"


def valuar(filas: list[dict]) -> dict[tuple[str, int], float]:
    usd_abiertas: list[list[float]] = []   # [dólares pendientes, TC de la factura]
    deudas_pesos: list[list[float]] = []   # [pesos pendientes]
    lotes: list[list] = []                 # [clave de la fila, pesos sin aplicar]
    credito_usd = 0.0                      # NC en dólares sin factura que cancelar
    val: dict[tuple[str, int], float] = defaultdict(float)

    def aplicar():
        nonlocal credito_usd
        while credito_usd > 1e-6 and usd_abiertas:
            x = min(credito_usd, usd_abiertas[0][0]); usd_abiertas[0][0] -= x; credito_usd -= x
            if usd_abiertas[0][0] <= 1e-6: usd_abiertas.pop(0)
        while lotes and (deudas_pesos or usd_abiertas):
            lote = lotes[0]
            if deudas_pesos:
                x = min(lote[1], deudas_pesos[0][0]); deudas_pesos[0][0] -= x; lote[1] -= x
                if deudas_pesos[0][0] <= 0.005: deudas_pesos.pop(0)
            else:
                usd, tc = usd_abiertas[0]
                x = min(lote[1], usd * tc); val[lote[0]] += x / tc; usd_abiertas[0][0] -= x / tc; lote[1] -= x
                if usd_abiertas[0][0] <= 1e-6: usd_abiertas.pop(0)
            if lote[1] <= 0.005: lotes.pop(0)

    for f in filas:
        clave = (f["origenTipo"], f["idOrigen"])
        if f["moneda"] == "Dolares":
            if f["deudaOriginal"]: usd_abiertas.append([f["deudaOriginal"], f["tipoDeCambio"]])
            if f["creditoOriginal"]: credito_usd += f["creditoOriginal"]
        else:
            val[clave] += 0.0
            if f["deudaOriginal"]: deudas_pesos.append([f["deudaOriginal"]])
            if f["creditoOriginal"]: lotes.append([clave, f["creditoOriginal"]])
        aplicar()
    print("Sin aplicar al final -> USD:", round(sum(u for u, _ in usd_abiertas), 4), " deudas $:",
          round(sum(d[0] for d in deudas_pesos), 2), " créditos $:", round(sum(l[1] for l in lotes), 2), " NC USD:", round(credito_usd, 4))
    return val


if __name__ == "__main__":
    raise SystemExit("REEMPLAZADO (18/10/2026) por scripts.aplicacion_lartirigoyen_036, que sigue las aplicaciones de Lartirigoyen. No correr: pisaría esa aplicación.")
    _assert_target_is_wc()
    filas = bimonetaria.cargar_cuenta(C, refrescar=True)["filas"]
    val = valuar(filas)
    print("Respaldo verificado:", backup_verificado("valuacion-lartirigoyen-036"))
    stmts = [("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ?", (C,))]
    stmts += [("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario, Fecha) "
               "VALUES (?, ?, ?, ?, ?, ?, 'Sergio (barrida 036)', SYSDATETIME())",
               (o, i, C, round(d, 4), FUENTE, "0 = documento de la subcuenta en pesos" if not d else None)) for (o, i), d in val.items()]
    execute_write_transaction(stmts)
    bimonetaria.invalidar()
    r = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("Saldo:", r["saldoPesos"], r["saldoDolares"])
