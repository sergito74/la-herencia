"""Reservas forrajeras (052 FR-021, T026): silos de maíz picado.

Sergio 26/11/2026: el silo es reserva y se consume cuando se necesita (mismo ejercicio, el siguiente u otro); no hay
regla fija. El consumo se registra (GanReservaConsumo, % o kg). El costo de la reserva es el "picado para silo" del
Resultado por cultivo (no se copia: se lee vivo).
- Con consumos registrados: cada consumo va al período de su fecha; lo no consumido queda como reserva valuada al costo.
- Sin ningún consumo registrado (silos viejos, sin datos): consumo ESTIMADO en el período siguiente a la confección,
  rotulado como estimado en pantalla.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from src.db.connection import execute_write, fetch_all
from src.features.ganaderia import periodos


def _registro() -> tuple[dict, dict]:
    res = {(r["idCultivo"], r["idCampania"]): r for r in fetch_all(
        "SELECT r.IdReserva id, r.Tipo tipo, r.Fecha fecha, r.IdCultivo idCultivo, r.IdCampania idCampania, r.Kg kg, "
        "r.Fuente fuente, r.Observaciones observaciones, c.Campaña campania FROM dbo.GanReserva r "
        "LEFT JOIN dbo.Campañas c ON c.IdCampaña = r.IdCampania WHERE r.Anulado = 0")}
    cons = defaultdict(list)
    for c in fetch_all("SELECT IdConsumo id, IdReserva idReserva, Fecha fecha, Kg kg, Porcentaje pct, Motivo motivo "
                       "FROM dbo.GanReservaConsumo WHERE Anulado = 0 ORDER BY Fecha, IdConsumo"):
        cons[c["idReserva"]].append(c)
    return res, cons


def fraccion(consumo: dict, kg_reserva) -> float:
    if consumo.get("pct") is not None:
        return float(consumo["pct"]) / 100
    return float(consumo["kg"]) / float(kg_reserva) if kg_reserva else 0.0


def imputar(pesos: float, usd: float, a0: int, consumos: list[dict], kg_reserva, vista: str) -> list[dict]:
    """Función pura: reparte el costo del silo en los períodos de consumo; sin consumos, estimado en a0+1 (ejercicio)."""
    if not consumos:
        return [{"periodo": a0 + (1 if vista == "ejercicio" else 0), "pesos": pesos, "usd": usd,
                 "detalle": "Consumo estimado (sin registro)"}]
    out = []
    for c in consumos:
        f = fraccion(c, kg_reserva)
        out.append({"periodo": periodos.anio_inicio(c["fecha"], vista), "pesos": pesos * f, "usd": usd * f,
                    "detalle": f"Consumo registrado {f:.0%}"})
    return out


def registro_de(id_cultivo: int, id_campania: int, cache: tuple | None = None) -> tuple[dict | None, list[dict]]:
    res, cons = cache or _registro()
    r = res.get((id_cultivo, id_campania))
    return r, (cons.get(r["id"], []) if r else [])


def reservas(fecha: date | None = None) -> dict:
    from src.features.ganaderia.costos import _resultado_cultivo_cache
    from src.features.resultado_cultivo.resultado import costo_cultivo_para_ganaderia

    fecha = fecha or date.today()
    res, cons = _registro()
    items, tot_p, tot_u = [], 0.0, 0.0
    for (idc, idcamp), r in sorted(res.items(), key=lambda x: str(x[1]["fecha"])):
        if str(r["fecha"])[:10] > fecha.isoformat():
            continue
        c = _resultado_cultivo_cache(idc, idcamp, costo_cultivo_para_ganaderia)
        p, u = float(c.get("costoSiloGanaderiaPesos") or 0), float(c.get("costoSiloGanaderiaDolares") or 0)
        lista = [x for x in cons.get(r["id"], []) if str(x["fecha"])[:10] <= fecha.isoformat()]
        if cons.get(r["id"]):
            consumido = min(sum(fraccion(x, r["kg"]) for x in lista), 1.0)
            estado = "Registrado"
        else:
            consumido = 1.0 if periodos.anio_inicio(fecha) > periodos.anio_campania_agricola(r["campania"]) + 1 else 0.0
            estado = "Estimado (sin registro)"
        saldo_p, saldo_u = p * (1 - consumido), u * (1 - consumido)
        tot_p, tot_u = tot_p + saldo_p, tot_u + saldo_u
        items.append({"id": r["id"], "tipo": r["tipo"], "campania": r["campania"], "fecha": str(r["fecha"])[:10],
                      "fuente": r["fuente"], "observaciones": r["observaciones"], "costoPesos": round(p, 2),
                      "costoDolares": round(u, 2), "pctConsumido": round(consumido * 100, 1), "estado": estado,
                      "saldoPesos": round(saldo_p, 2), "saldoDolares": round(saldo_u, 2),
                      "consumos": [{"id": x["id"], "fecha": str(x["fecha"])[:10],
                                    "pct": round(fraccion(x, r["kg"]) * 100, 1), "motivo": x["motivo"]}
                                   for x in cons.get(r["id"], [])]})
    return {"fecha": fecha.isoformat(), "items": items, "saldoPesos": round(tot_p, 2), "saldoDolares": round(tot_u, 2)}


def registrar_consumo(id_reserva: int, fecha: date, porcentaje: float, motivo: str | None, usuario: str | None) -> None:
    if not 0 < porcentaje <= 100:
        raise ValueError("El porcentaje va de 0 a 100")
    hecho = fetch_all("SELECT ISNULL(SUM(Porcentaje),0) p FROM dbo.GanReservaConsumo WHERE IdReserva = ? AND Anulado = 0",
                      (id_reserva,))[0]["p"]
    if float(hecho) + porcentaje > 100.0001:
        raise ValueError(f"Ya hay {float(hecho):.0f} % consumido; no puede pasar de 100 %")
    execute_write("INSERT INTO dbo.GanReservaConsumo (IdReserva, Fecha, Porcentaje, Motivo, Usuario) VALUES (?, ?, ?, ?, ?)",
                  (id_reserva, fecha, porcentaje, (motivo or "").strip() or None, usuario))


def anular_consumo(id_consumo: int) -> None:
    execute_write("UPDATE dbo.GanReservaConsumo SET Anulado = 1 WHERE IdConsumo = ?", (id_consumo,))
