r"""035 — Valuación en dólares de FEDEA (217) según su propio libro (portal extranet, consulta de solo lectura del 08/10/2026).

Carga en `ValuacionProveedor` los dólares que FEDEA acreditó o debitó por cada fila de la cuenta cuando difieren (>= US$ 0,50)
de lo que calcula el motor con el dólar BNA. Evidencia: libro unificado en dólares 2015-2016 (leído del portal), 2017-2018
(portal) y los estados de cuenta de `Resumenes de Cuenta\FEDEA`. Signo de los importes: + = a favor nuestro (haber - debe).

Uso (desde backend/):
    python -m scripts.cargar_valuacion_fedea_035 --simular   # lista lo que cargaría
    python -m scripts.cargar_valuacion_fedea_035             # respaldo verificado y carga (reejecutable)
"""

from __future__ import annotations

import sys
from datetime import date

from src.db.connection import execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria as b
from src.features.vinculos.backup import backup_verificado

ID = 217
U = "Sergio (grupo 4, auditoría 035)"
FUENTE = "Libro en dólares de FEDEA (portal extranet, consulta del 08/10/2026)"

DOCS_2015_2016 = {
 "0103-00019282": -343.04,
 "0103-00019283": -2025.53,
 "0103-00019284": -56.46,
 "0103-00019285": -4625.11,
 "0103-00019286": -119.34,
 "0103-00019498": -2405.48,
 "0103-00019836": 2435.3,
 "0103-00019858": -2405.48,
 "0103-00019859": 0.0,
 "0103-00019955": 724.35,
 "0103-00020098": -890.56,
 "0103-00020099": -2560.36,
 "0103-00020100": -243.1,
 "0103-00020299": 7.26,
 "0103-00020310": -7.26,
 "0103-00020790": -24.58,
 "0103-00020847": 0.86,
 "0103-00021505": -1482.25,
 "0103-00021506": -110.5,
 "0103-00021555": 1337.05,
 "0103-00021617": -1337.05,
 "0103-00021655": -1875.74,
 "0103-00021656": -2958.64,
 "1003-00000045": -914.76,
 "0103-00021826": 0.0,
 "0103-00021827": -0.47,
 "1003-00000022": -423.23,
 "1003-00000023": -2492.83,
 "1003-00000034": -24.1,
 "1003-00000035": -28.52,
 "1003-00000081": -31.83,
 "1003-00000048": 0.0,
 "1003-00000049": 0.59,
 "1003-00000050": 0.0,
 "1003-00000125": 0.0,
 "1003-00000331": -8089.46,
 "1003-00000332": -11288.09,
 "1003-00000333": -3069.17,
 "1003-00000334": -2.9,
 "1003-00000335": -116.03,
 "1003-00000280": 526.35,
 "1003-00000367": -526.35,
 "1003-00000291": 81.68,
 "1003-00000395": -1373.96,
 "1003-00000296": 1292.28,
 "1003-00000407": -1361.25,
 "1003-00000915": -1467.61,
 "1003-00000943": -116.16,
 "1003-00000516": 116.16
}
LIQ_2015_2016 = {
 "05644229": 6247.84,
 "05645080": 3577.03,
 "05645144": 2285.1,
 "05750942": 285.15,
 "05751001": 162.92,
 "05751036": 114.24
}

# 2017-2018 (unificada, dólares); solo las líneas "NO" de las liquidaciones: la parte canje y su compensación se anulan entre sí
DOCS_2017_2018 = {
    "1003-00000806": 62.80, "1003-00001497": -2880.37, "1003-00001498": -23.85, "1003-00000948": 946.72, "1003-00001499": -44.71,
    "1003-00001507": -6.18, "1003-00001509": 0.0, "1003-00001703": -4242.19, "1003-00001704": -641.38, "1003-00001710": -40.26,
    "1003-00001711": -130.32, "1003-00001732": 0.0, "1003-00001175": 0.0, "1003-00001876": -39.50, "1003-00002291": -122.88,
    "1003-00002364": -28.95, "1003-00002688": -302.74, "1003-00002802": 0.0, "1003-00001840": 0.0,
    "1003-00002927": -111.29, "1003-00002928": -734.95, "1003-00002929": -525.96, "1003-00002930": -111.29, "1003-00002931": -333.86,
    "1003-00002990": -13.37, "1003-00005018": 0.0, "1003-00006360": -8.12, "1003-00006375": 0.0,
}
LIQ_2017_2018 = {"07786691": 8289.96, "07786787": 7156.74, "07786809": 1287.12, "07821403": 857.55, "07821828": 754.57, "07821948": 137.96,
                 "08247073": 21967.76, "08247191": 341.26, "10841540": 1856.91, "10841674": 3285.42}

# pagos y cobros: (descripción, pesos de las filas del sistema, dólares que FEDEA acreditó (+) o debitó (-))
PAGOS = [
    ("RC 4869", [22931.44], 2403.71), ("RC 5108", [30000.00, 31990.00], 6417.18), ("RC 5137", [35750.72], 3694.02), ("RC 5243", [1771.76], 123.38),
    ("OP 66196", [-32802.62], -2311.67), ("OP 66803", [-1639.87], -115.48), ("AD 1166", [-349.48], -23.33),
    ("OP 79560", [-145057.61], -9277.75), ("OP 79791", [-13771.71], -892.53),
    ("RC 6194", [60036.04], 3219.26), ("RC 6195", [149888.08], 9867.55), ("RC 6253", [2107.00], 130.46), ("RC 6308", [30751.45], 1863.72),
    ("ADI 1074", [-8.02], 0.0), ("ACI 1101", [27.65], 0.0), ("ACI 1145", [-5.13], 0.0), ("AD 1226", [-103.04], -4.17),
    ("RC 6889", [13473.85, 5.91, 3264.24, 1.43], 887.41), ("RC 7175", [6131.09], 235.81), ("OP 98788", [-85175.00, 4483.15 * -1], -3267.43),
]
UMBRAL = 0.50


def filas_con_dolares() -> list[dict]:
    c = b.cargar_cuenta(ID, refrescar=True)
    prev, out = 0.0, []
    for x in c["filas"]:
        out.append({**x, "usd": round(x["saldoDolares"] - prev, 4), "pesos": round(x["creditoPesos"] - x["deudaPesos"], 2)})
        prev = x["saldoDolares"]
    return out


def calcular() -> list[tuple[str, int, float, str]]:
    filas = filas_con_dolares()
    docs = {**DOCS_2015_2016, **DOCS_2017_2018}
    liq = {**LIQ_2015_2016, **LIQ_2017_2018}
    res: list[tuple[str, int, float, str]] = []
    for x in filas:
        if x["origenTipo"] == "Compras" and x["moneda"] == "Pesos" and (x["numeroDocumento"] in docs):
            fe = docs[x["numeroDocumento"]]
            motivo = f"{x['documento']} {x['numeroDocumento']}"
        elif x["origenTipo"] == "Venta Granos" and (x["numeroDocumento"] or "")[-8:] in liq:
            fe = liq[x["numeroDocumento"][-8:]]
            motivo = f"Liquidación {x['numeroDocumento']}"
        else:
            continue
        if abs(x["usd"] - fe) >= UMBRAL:
            res.append((x["origenTipo"], x["idOrigen"], abs(fe), motivo + f" (FEDEA {fe:+,.2f}; motor {x['usd']:+,.2f})"))
    # pagos: se ubican por el importe en pesos y se reparte lo de FEDEA en proporción
    usados: set[int] = set()
    for desc, pesos, usd in PAGOS:
        elegidas = []
        for p in pesos:
            cand = [i for i, x in enumerate(filas) if i not in usados and x["origenTipo"] not in ("Compras", "Venta Granos", "Ajuste Interno")
                    and abs(abs(x["pesos"]) - abs(p)) < 0.005]
            if not cand:
                print("  sin fila para", desc, p)
                continue
            usados.add(cand[0])
            elegidas.append(cand[0])
        if not elegidas:
            continue
        total = sum(abs(filas[i]["pesos"]) for i in elegidas)
        motor = sum(filas[i]["usd"] for i in elegidas)
        # el signo de FEDEA debe coincidir con el de la fila; si no, no se toca
        if abs(motor - usd) < UMBRAL:
            continue
        for i in elegidas:
            x = filas[i]
            parte = abs(usd) * (abs(x["pesos"]) / total)
            res.append((x["origenTipo"], x["idOrigen"], round(parte, 4), f"{desc} (FEDEA {usd:+,.2f} en total; motor {motor:+,.2f})"))
    return res


def main(simular: bool) -> None:
    res = calcular()
    print(f"{len(res)} filas con diferencia de valuación:")
    for o, i, d, m in res:
        print(f"  {o:14} {i:>12} US$ {d:>10,.2f}  {m}")
    if simular:
        return
    bk = backup_verificado("valuacion-fedea-035")
    print("Respaldo:", bk)
    stm = [("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ?", (ID,))]
    for o, i, d, m in res:
        stm.append(("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (o, i, ID, d, FUENTE, m[:400], U)))
    execute_write_transaction(stm)
    b.invalidar()
    c = b.cargar_cuenta(ID, refrescar=True)
    print("saldo: pesos", c["saldoPesos"], "dólares", c["saldoDolares"])


if __name__ == "__main__":
    main("--simular" in sys.argv)
