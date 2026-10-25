"""Vínculo socio ↔ contacto (Sergio, 24/10/2026: «no confundamos cajas con cuentas corrientes»).

La cuenta de socio (MovimientosCuentaSocio, valuada en US$/kg) es la ÚNICA cuenta oficial del socio. El contacto
solo identifica de quién es un movimiento de banco o un pago; su saldo en pesos nominales no es la deuda del socio.
El control cruza los movimientos bancarios del contacto con los asientos del socio para que nada quede sin su par.
"""

from __future__ import annotations

from datetime import date, datetime

from src.db.connection import fetch_all

# IdSocio -> IdContacto «lado bancario». 375 (Sergio empleado) queda fuera: solo sueldos. Ceci = Virginia (564).
SOCIO_CONTACTO = {1: 5670, 2: 390, 3: 549, 4: 564}
CONTACTO_SOCIO = {v: k for k, v in SOCIO_CONTACTO.items()}
ORIGENES_BANCO = ("Banco Nacion", "Galicia", "Mercado Pago", "Conciliación Tesorería")
DIAS = 5
NOMBRE_EN_CONDOMINIO = {1: "Sergio", 2: "Lucy", 4: "Ceci"}
# Movimientos explicados por Sergio que no llevan asiento (origen de la vista, IdOrigen) -> explicación.
EXPLICADOS = {
    ("Banco Nacion", 18536): "Retiro de ganancias del 10/08/2017 (Sergio, 25/10/2026): no va a la cuenta de socio",
}
SOCIO_NOMBRE = {1: "Sergio", 2: "Lucy", 3: "Cond LSC", 4: "Ceci"}


def mapa() -> list[dict]:
    nombres = {r["IdSocio"]: r["Nombre"] for r in fetch_all("SELECT IdSocio, Nombre FROM dbo.Socios")}
    return [{"idSocio": s, "socio": nombres.get(s), "idContacto": c} for s, c in SOCIO_CONTACTO.items()]


def _dia(x) -> date:
    return x.date() if isinstance(x, datetime) else date.fromisoformat(str(x)[:10])


def control_banco(id_socio: int) -> dict:
    """Movimientos de banco del contacto del socio sin asiento en la cuenta de socio (mismo importe, ±5 días)."""
    contacto = SOCIO_CONTACTO.get(id_socio)
    if contacto is None:
        return {"idContacto": None, "banco": 0, "conAsiento": 0, "sinAsiento": [], "enCuentaCondominio": []}
    marks = ",".join("?" for _ in ORIGENES_BANCO)
    banco = fetch_all(
        f"SELECT Fecha, Documento, [Nro Documento] nro, CAST(Deuda AS float) deuda, CAST(Credito AS float) credito, Origen, IdOrigen "
        f"FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=? AND Origen IN ({marks}) ORDER BY Fecha", (contacto, *ORIGENES_BANCO))
    asientos = [{"fecha": _dia(r["Fecha"]), "importe": round(float(r["Importe"]), 2), "usado": False} for r in fetch_all(
        "SELECT Fecha, Importe FROM dbo.MovimientosCuentaSocio WHERE IdSocio=? AND Anulada=0", (id_socio,))]
    # Retiros del socio registrados en la cuenta del Condominio («<socio> — Retiro por aporte…»): el Condominio aporta y
    # Giamigli transfiere a cada socio su parte (Sergio 24/10/2026). Se cruzan con tolerancia de $10 por redondeo de tercios.
    nombre = NOMBRE_EN_CONDOMINIO.get(id_socio)
    en_cond = [{"fecha": _dia(r["Fecha"]), "importe": round(float(r["Importe"]), 2), "usado": False, "motivo": r["Motivo"]} for r in fetch_all(
        "SELECT Fecha, Importe, Motivo FROM dbo.MovimientosCuentaSocio WHERE IdSocio=3 AND Anulada=0 AND Tipo='AsignacionGasto' AND Motivo LIKE ?",
        (f"{nombre} —%",))] if nombre else []
    sin, via_cond = [], []
    for b in banco:
        importe = round(abs((b["credito"] or 0) - (b["deuda"] or 0)), 2)
        f = _dia(b["Fecha"])
        par = next((a for a in asientos if not a["usado"] and a["importe"] == importe and abs((a["fecha"] - f).days) <= DIAS), None)
        cond = None if par else next((a for a in en_cond if not a["usado"] and abs(a["importe"] - importe) <= 10
                                      and abs((a["fecha"] - f).days) <= DIAS), None)
        combo = None if (par or cond) else _combinacion(importe, f, id_socio)
        explicado = None if (par or cond or combo) else _explicacion(b, importe, f, id_socio)
        if explicado:
            via_cond.append({"fecha": f.isoformat(), "importe": importe, "diferencia": 0.0, "asiento": explicado})
            continue
        if par:
            par["usado"] = True
        elif combo:
            via_cond.append({"fecha": f.isoformat(), "importe": importe, "diferencia": 0.0,
                             "asiento": " + ".join(f"{c['socio']}: {c['motivo']} {c['importe']:,.2f}" for c in combo)})
        elif cond:
            cond["usado"] = True
            via_cond.append({"fecha": f.isoformat(), "importe": importe, "asiento": cond["motivo"],
                             "diferencia": round(importe - cond["importe"], 2)})
        else:
            sin.append({"fecha": f.isoformat(), "origen": b["Origen"], "idOrigen": b["IdOrigen"], "documento": b["Documento"],
                        "importe": importe, "sentido": "ingreso a Giamigli" if (b["deuda"] or 0) > (b["credito"] or 0) else "egreso de Giamigli"})
    return {"idContacto": contacto, "banco": len(banco), "conAsiento": len(banco) - len(sin), "sinAsiento": sin,
            "enCuentaCondominio": via_cond}


def _combinacion(importe: float, fecha: date, id_socio: int) -> list[dict] | None:
    """Una transferencia de banco que se reparte en 2 o 3 asientos del mismo día (±5), del socio o de los otros socios,
    p. ej. un lote de $400.000 = $200.000 Sergio + $200.000 Lucy (01/08/2022), o $650.000 = $350.000 en la cuenta de
    Sergio + $300.000 «Sergio — Retiro…» en la del Condominio (11/11/2025). Importe exacto."""
    from datetime import timedelta
    from itertools import combinations

    filas = fetch_all(
        "SELECT m.IdSocio, s.Nombre, m.Fecha, m.Importe, m.Motivo FROM dbo.MovimientosCuentaSocio m JOIN dbo.Socios s ON s.IdSocio=m.IdSocio "
        "WHERE m.Anulada=0 AND m.Tipo='AsignacionGasto' AND m.Fecha BETWEEN ? AND ?",
        ((fecha - timedelta(days=DIAS)).isoformat(), (fecha + timedelta(days=DIAS)).isoformat()))
    nombre = NOMBRE_EN_CONDOMINIO.get(id_socio, "")
    cands = [{"socio": r["Nombre"], "importe": round(float(r["Importe"]), 2), "motivo": r["Motivo"]} for r in filas
             if r["IdSocio"] == id_socio or (r["IdSocio"] == 3 and str(r["Motivo"]).startswith(f"{nombre} —"))
             or "devolucion por aporte" in str(r["Motivo"]).lower().replace("ó", "o") or "lote haberes" in str(r["Motivo"])]
    for n in (2, 3):
        for c in combinations(cands, n):
            if abs(sum(x["importe"] for x in c) - importe) < 0.005 and any(x["socio"] == SOCIO_NOMBRE.get(id_socio) or
                                                                         str(x["motivo"]).startswith(f"{nombre} —") for x in c):
                return list(c)
    return None


def _explicacion(b: dict, importe: float, fecha: date, id_socio: int) -> str | None:
    """Movimientos de banco del socio que NO llevan asiento en su cuenta, por reglas de Sergio:
    - pase banco → caja: Giamigli le transfiere y el mismo día él deposita lo mismo en la caja como «Aporte Efectivo»
      (es efectivo de Giamigli que cambia de lugar; no es aporte ni retiro del socio);
    - retiro de ganancias (no genera deuda), según la explicación registrada al reasignar el movimiento."""
    if (b["Origen"], b["IdOrigen"]) in EXPLICADOS:
        return EXPLICADOS[(b["Origen"], b["IdOrigen"])]
    nombre = SOCIO_NOMBRE.get(id_socio, "")
    caja = fetch_all(
        "SELECT TOP 1 IdMovimiento FROM dbo.MovimientosCajaEfectivo WHERE Anulada=0 AND Caja='GiamigliSA' AND Importe=? "
        "AND Concepto LIKE 'Aporte Efectivo%' AND Fecha BETWEEN DATEADD(day,-2,?) AND DATEADD(day,2,?) AND ISNULL(Detalle,'') + Concepto LIKE ?",
        (importe, fecha.isoformat(), fecha.isoformat(), "%"))
    if caja and (b["deuda"] or 0) < (b["credito"] or 0):
        return f"Pase banco → caja Giamigli (caja mov. {caja[0]['IdMovimiento']}, «Aporte Efectivo» del mismo día): sin efecto en la cuenta de {nombre}"
    medio = {"Banco Nacion": ("bna", "Banco Nacion", "Banco Nación"), "Galicia": ("galicia", "Galicia")}.get(b["Origen"], ())
    if medio:
        marks = ",".join("?" for _ in medio)
        r = fetch_all(f"SELECT TOP 1 Motivo FROM dbo.ReasignacionesContacto WHERE IdOrigen=? AND Origen IN ({marks}) "
                      "AND Motivo LIKE '%GANANCIAS%' ORDER BY Fecha DESC", (b["IdOrigen"], *medio))
        if r:
            return f"Retiro de ganancias (no va a la cuenta de socio): {r[0]['Motivo']}"
    return None
