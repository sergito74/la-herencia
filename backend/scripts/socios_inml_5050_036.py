"""036: histórico oficial INML y revaluación 50/50 aprobada el 25/10/2026.

Inspección por defecto. Cachea los HTML oficiales y sus hashes en backups/.
--aplicar requiere backup WC verificado, revalida el plan bajo bloqueo y
escribe índices/asientos/auditoría en una sola transacción. No cambia pesos,
tipos, fechas, vínculos ni asientos anulados. Mutuo y billetes USD excluidos.
"""

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from bisect import bisect_right
from datetime import date, datetime
from pathlib import Path

from src.db.connection import _assert_target_is_wc, _reconciliation_connection, reconciliation_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_socios.valuacion import calcular
from src.features.pastaje.inmag import URL, parsear
from src.features.vinculos.backup import backup_verificado
from scripts.vincular_tres_pagos_condominio_036 import control

RULE = "socios-inml-5050-20261025-036"
FOLDER = Path(__file__).resolve().parents[2] / "backups" / RULE


def dump(path, obj):
    path.write_text(json.dumps(obj, default=str, ensure_ascii=False, indent=2), encoding="utf-8")


def dia(value):
    return date.fromisoformat(str(value)[:10])


def historico():
    FOLDER.mkdir(parents=True, exist_ok=True)
    fechas, fuentes = {}, []
    for year in range(2011, 2021):
        ini, fin = date(year, 1, 1), min(date(year, 12, 31), date(2020, 3, 2))
        path = FOLDER / f"inml-{ini}-{fin}.html"
        if not path.exists():
            datos = urllib.parse.urlencode({
                "ID": "", "CP": "", "FLASH": "", "USUARIO": "SIN IDENTIFICAR",
                "OPCIONMENU": "", "OPCIONSUBMENU": "",
                "txtFechaIni": ini.strftime("%d/%m/%Y"), "txtFechaFin": fin.strftime("%d/%m/%Y"),
            }).encode()
            req = urllib.request.Request(URL, data=datos, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw = resp.read()
            # No cachear páginas de error ni respuestas fuera del intervalo.
            rows = parsear(raw.decode("latin-1"))
            if not rows or not all(ini <= f <= fin for f, _, _ in rows):
                raise ValueError(f"Respuesta histórica inválida {year}")
            path.write_bytes(raw)
        raw = path.read_bytes()
        rows = parsear(raw.decode("latin-1"))
        if not rows or not all(ini <= f <= fin for f, _, _ in rows):
            raise ValueError(f"Cache inválido {year}")
        for f, cab, valor in rows:
            if valor is not None and valor > 0:
                if f in fechas and fechas[f] != (cab, valor):
                    raise ValueError(f"Índice duplicado contradictorio {f}")
                fechas[f] = (cab, valor)
        fuentes.append({"archivo": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
                        "desde": ini, "hasta": fin, "filas": len(rows), "url": URL})
    dump(FOLDER / "fuentes.json", fuentes)
    return fechas


def at(series, fecha):
    dias = sorted(series)
    i = bisect_right(dias, fecha) - 1
    if i < 0:
        raise ValueError(f"Falta cotización anterior a {fecha}")
    return dias[i], series[dias[i]]


def rows(cursor, sql):
    cursor.execute(sql)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r, strict=True)) for r in cursor.fetchall()]


def run(aplicar=False, posteriores=False):
    _assert_target_is_wc()
    regla = RULE + ("-posteriores" if posteriores else "")
    if read("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (regla,)):
        return {"estado": "ya_aplicado_sin_escrituras"}
    hist = historico()
    existentes = read("SELECT Fecha,Indice,CabIngresadas FROM dbo.IndiceINMAG ORDER BY Fecha")
    nov = {dia(r["Fecha"]): r["Indice"] for r in existentes}
    nuevas = [(f, cab, v) for f, (cab, v) in sorted(hist.items()) if f not in nov]
    nov.update({f: v for f, _, v in nuevas})
    dol = {dia(r["Fecha"]): r["Prom_billete"] for r in read(
        "SELECT Fecha,Prom_billete FROM dbo.[Dolar BNA] WHERE Prom_billete>0 ORDER BY Fecha")}
    antes = read("SELECT * FROM dbo.MovimientosCuentaSocio ORDER BY IdMovimiento")
    cambios = []
    for r in antes:
        if (r["Anulada"] or (dia(r["Fecha"]) < date(2020, 3, 16)) == posteriores
                or r["Origen"] == "Mutuo2018" or "dolar" in (r["Medio"] or "").lower()
                or "dólar" in (r["Medio"] or "").lower()):
            continue
        f = dia(r["Fecha"])
        fd, d = at(dol, f)
        fn, n = at(nov, f)
        valor = calcular(r["Importe"], f, d, n)
        if r["ImporteUSD"] != valor["importeUSD"] or r["ImporteKgCarne"] != valor["importeKgCarne"]:
            if (f - fd).days > 10 or (f - fn).days > 10:
                raise ValueError(f"Cotización demasiado distante para cambiar asiento {r['IdMovimiento']}")
            cambios.append({"id": r["IdMovimiento"], "socio": r["IdSocio"], "antesUSD": r["ImporteUSD"],
                            "antesKg": r["ImporteKgCarne"], **valor, "fechaDolar": fd, "dolar": d,
                            "fechaNovillo": fn, "novillo": n})
    resultado = {"estado": "inspeccion", "indicesNuevos": len(nuevas), "asientos": len(cambios),
                 "porSocio": {s: sum(c["socio"] == s for c in cambios) for s in (1, 2, 3, 4)},
                 "fuentes": str(FOLDER / "fuentes.json"), "cambios": cambios}
    dump(FOLDER / ("plan-posteriores.json" if posteriores else "plan.json"), resultado)
    if not aplicar:
        return {k: v for k, v in resultado.items() if k != "cambios"}
    respaldo = backup_verificado("socios_inml_5050_036" + ("_posteriores" if posteriores else ""))
    snapshot = FOLDER / f"aplicacion-{datetime.now():%Y%m%d-%H%M%S}.json"
    resultado.update(backupVerificado=respaldo, antes=antes, indicesAntes=existentes)
    dump(snapshot, resultado)
    with reconciliation_transaction():
        c = _reconciliation_connection.get().cursor()
        actual = rows(c, "SELECT * FROM dbo.MovimientosCuentaSocio WITH (UPDLOCK,HOLDLOCK) ORDER BY IdMovimiento")
        if actual != antes:
            raise ValueError("Cambiaron los asientos: recalcular el plan")
        indices = rows(c, "SELECT Fecha,Indice,CabIngresadas FROM dbo.IndiceINMAG WITH (UPDLOCK,HOLDLOCK) ORDER BY Fecha")
        dolares = rows(c, "SELECT Fecha,Prom_billete FROM dbo.[Dolar BNA] WITH (HOLDLOCK) WHERE Prom_billete>0 ORDER BY Fecha")
        if indices != existentes or {dia(r["Fecha"]): r["Prom_billete"] for r in dolares} != dol:
            raise ValueError("Cambiaron las cotizaciones: recalcular el plan")
        controles = control(c)
        for f, cab, valor in nuevas:
            c.execute("INSERT INTO dbo.IndiceINMAG (Fecha,Indice,CabIngresadas,Origen,Fuente,Nota) VALUES (?,?,?,'auto',?,?)",
                      f.isoformat(), str(valor), cab, URL, "Histórico INML Mercado de Liniers; continuidad INMAG. Sergio 25/10/2026. " + RULE)
        for r in cambios:
            c.execute("UPDATE dbo.MovimientosCuentaSocio SET ImporteUSD=?,ImporteKgCarne=? OUTPUT INSERTED.IdMovimiento WHERE IdMovimiento=?",
                      str(r["importeUSD"]), str(r["importeKgCarne"]), r["id"])
            if [row[0] for row in c.fetchall()] != [r["id"]]:
                raise ValueError("Asiento no actualizado")
        despues = rows(c, "SELECT * FROM dbo.MovimientosCuentaSocio ORDER BY IdMovimiento")
        esperado = {r["id"]: r for r in cambios}
        for a, d in zip(antes, despues, strict=True):
            e = dict(a)
            if a["IdMovimiento"] in esperado:
                v = esperado[a["IdMovimiento"]]
                e.update(ImporteUSD=v["importeUSD"], ImporteKgCarne=v["importeKgCarne"])
            if e != d:
                raise ValueError(f"Cambio fuera de alcance {a['IdMovimiento']}")
        controles_despues = control(c)
        if controles["cajas"] != controles_despues["cajas"] or controles["cuentas"] != controles_despues["cuentas"]:
            raise ValueError("Cambió una caja o cuenta corriente")
        resultado.update(estado="aplicado", controlesAntes=controles, controlesDespues=controles_despues,
                         despues=despues, snapshot=str(snapshot))
        c.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)",
                  regla, json.dumps({"snapshot": str(snapshot), "cambios": cambios}, default=str, ensure_ascii=False),
                  respaldo, f"Histórico INML: {len(nuevas)} índices; {len(cambios)} asientos 50/50 {'posteriores' if posteriores else 'pre2020'}. Nominales, cajas, proveedores, mutuo y billetes preservados.")
    dump(snapshot, resultado)
    return {k: v for k, v in resultado.items() if k not in ("cambios", "antes", "despues", "indicesAntes", "controlesAntes", "controlesDespues")}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--aplicar", action="store_true")
    p.add_argument("--posteriores", action="store_true", help="Conciliar también valuaciones ordinarias desde 16/03/2020 con las cotizaciones vigentes de cada fecha")
    args = p.parse_args()
    print(json.dumps(run(args.aplicar, args.posteriores), default=str, ensure_ascii=False, indent=2))
