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
        if par:
            par["usado"] = True
        elif cond:
            cond["usado"] = True
            via_cond.append({"fecha": f.isoformat(), "importe": importe, "asiento": cond["motivo"],
                             "diferencia": round(importe - cond["importe"], 2)})
        else:
            sin.append({"fecha": f.isoformat(), "origen": b["Origen"], "idOrigen": b["IdOrigen"], "documento": b["Documento"],
                        "importe": importe, "sentido": "ingreso a Giamigli" if (b["deuda"] or 0) > (b["credito"] or 0) else "egreso de Giamigli"})
    return {"idContacto": contacto, "banco": len(banco), "conAsiento": len(banco) - len(sin), "sinAsiento": sin,
            "enCuentaCondominio": via_cond}
