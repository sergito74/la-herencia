"""Plan por tandas para aplicar el FIFO a todos los contactos — 035 (Historia 3, T024–T026).

A partir de una simulación de todos los contactos arma tandas pequeñas, de las cuentas más fáciles a las más complicadas,
para que Sergio revise y apruebe de a una. Cada tanda se simula y se aplica por separado con el motor del FIFO (032):
respaldo verificado, saldos intactos y reversión exacta.

`armar_tandas` es pura; el resto lee las tablas de la simulación (solo lectura).
"""

from __future__ import annotations

import json

from src.db.connection import fetch_all, fetch_one

TAMANO_TANDA = 50
# De las cuentas más fáciles (poco volumen) a las más complicadas; las de dólares van aparte, al final.
CORTES = [(250_000, "hasta $ 250.000"), (1_000_000, "de $ 250.000 a $ 1 M"), (5_000_000, "de $ 1 M a $ 5 M"), (float("inf"), "más de $ 5 M")]


def _rango(volumen: float) -> int:
    return next(i for i, (corte, _) in enumerate(CORTES) if volumen < corte)


def armar_tandas(contactos: list[dict], tamano: int = TAMANO_TANDA) -> list[dict]:
    """Agrupa por rango de volumen (en pesos) y luego las de dólares; alfabético dentro de cada grupo; tandas de hasta `tamano`."""
    grupos: dict[tuple[int, str], list[dict]] = {}
    for c in contactos:
        if c["moneda"] != "ARS":
            clave = (len(CORTES), "cuentas en dólares")
        else:
            i = _rango(float(c["volumen"]))
            clave = (i, CORTES[i][1])
        grupos.setdefault(clave, []).append(c)
    tandas = []
    for (orden, rango), lista in sorted(grupos.items()):
        lista = sorted(lista, key=lambda c: ((c["nombre"] or "").casefold(), c["idContacto"]))
        partes = [lista[i:i + tamano] for i in range(0, len(lista), tamano)]
        for n, parte in enumerate(partes, start=1):
            tandas.append({"numero": len(tandas) + 1, "rango": rango, "parte": f"{n} de {len(partes)}", "contactos": parte,
                           "desde": parte[0]["nombre"], "hasta": parte[-1]["nombre"]})
    return tandas


def simulacion_base() -> dict | None:
    """La última simulación de todos los contactos."""
    f = fetch_one("SELECT TOP 1 IdEjecucion AS id, FechaInicio AS fecha, Resumen AS resumen FROM dbo.RecalculoFifoEjecucion "
                  "WHERE Tipo = 'simulacion' AND Alcance = '\"todos\"' ORDER BY IdEjecucion DESC", ())
    return None if f is None else {"idEjecucion": f["id"], "fecha": f["fecha"], "resumen": json.loads(f["resumen"] or "{}")}


def contactos_aplicados_desde(id_base: int) -> set[int]:
    aplicados: set[int] = set()
    for f in fetch_all("SELECT Resumen AS r FROM dbo.RecalculoFifoEjecucion WHERE Estado = 'aplicada' AND IdEjecucion > ?", (id_base,)):
        try:
            resumen = json.loads(f["r"] or "{}")
            # una cuenta que no necesitó cambios también quedó resuelta por esa tanda
            aplicados |= set(resumen.get("aplicados", [])) | set(resumen.get("sinCambios", []))
        except ValueError:
            continue
    return aplicados


def plan() -> dict:
    base = simulacion_base()
    if base is None:
        return {"base": None, "tandas": [], "excepciones": []}
    filas = fetch_all(
        "SELECT IdContacto AS id, Nombre AS n, Moneda AS m, Volumen AS v, Saldo AS s, Tendencia AS t, CierraDespues AS cd, "
        "AplicadoAntes AS aa, AplicadoDespues AS ad FROM dbo.RecalculoFifoContacto WHERE IdEjecucion = ?", (base["idEjecucion"],))
    aplicados = contactos_aplicados_desde(base["idEjecucion"])
    mejoran = [{"idContacto": f["id"], "nombre": f["n"], "moneda": f["m"], "volumen": float(f["v"]), "saldo": float(f["s"])}
               for f in filas if f["t"] == "mejora" and f["cd"]]
    tandas = armar_tandas(mejoran)
    for t in tandas:
        hechos = sum(1 for c in t["contactos"] if c["idContacto"] in aplicados)
        t["aplicados"] = hechos
        t["estado"] = "aplicada" if hechos == len(t["contactos"]) else ("parcial" if hechos else "pendiente")
    excepciones = [{"idContacto": f["id"], "nombre": f["n"], "moneda": f["m"], "volumen": float(f["v"]), "saldo": float(f["s"])}
                   for f in sorted(filas, key=lambda f: -float(f["v"])) if not f["cd"]]
    return {"base": base, "yaCierran": sum(1 for f in filas if f["t"] == "igual" and f["cd"]), "tandas": tandas, "excepciones": excepciones}
