"""039: índice INMAG diario (Mercado Agroganadero de Cañuelas, haciinfo000011).

La serie histórica es INML del Mercado de Liniers, continuada por INMAG
(aclaración de Sergio, 25/10/2026); se conserva en la misma serie con su fuente.
Es el índice pactado en los contratos de pastaje y, por FR-019, el único índice de
novillo del sistema. Días sin índice publicado ("- *", menos de 300 novillos) no se
guardan. Las cantidades usan '.' como separador de miles.
"""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from decimal import Decimal

from src.db.connection import execute_write_transaction, fetch_all, fetch_one

DIAS_PARA_FIJAR = 2
URL = "https://www.mercadoagroganadero.com.ar/dll/hacienda2.dll/haciinfo000011"
_FILA = re.compile(
    r'<TD Align="Center">\w\w&nbsp;(\d\d/\d\d/\d{4})</TD><TD Align="Right">([^<]*)</TD>'
    r'<TD Align="Right">[^<]*</TD><TD Align="Center">([^<]*)</TD>'
)


_TOTAL = re.compile(r"Totales</B></TD>(?:<TD[^>]*><B>[^<]*</B></TD>){2}<TD[^>]*><B>([\d.]+,\d+)</B>")


def parsear(html: str) -> list[tuple[date, int, Decimal | None]]:
    out = []
    for f, cab, ind in _FILA.findall(html):
        ind = ind.replace("*", "").strip()
        valor = Decimal(ind.replace(".", "").replace(",", ".")) if re.fullmatch(r"[\d.]+,\d+", ind) else None
        cab = cab.strip().replace(".", "")
        out.append((datetime.strptime(f, "%d/%m/%Y").date(), int(cab) if cab.isdigit() else 0, valor if valor else None))
    return out


def _pedir(desde: date, hasta: date) -> str:
    datos = urllib.parse.urlencode({
        "ID": "", "CP": "", "FLASH": "", "USUARIO": "SIN IDENTIFICAR", "OPCIONMENU": "", "OPCIONSUBMENU": "",
        "txtFechaIni": desde.strftime("%d/%m/%Y"), "txtFechaFin": hasta.strftime("%d/%m/%Y"),
    }).encode()
    req = urllib.request.Request(URL, data=datos, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=120).read().decode("latin-1")


def promedio_publicado(desde: date, hasta: date) -> Decimal | None:
    """Fila "Totales" del mercado para el rango: importe ÷ kilos de los novillos del período."""
    m = _TOTAL.search(_pedir(desde, hasta))
    return Decimal(m.group(1).replace(".", "").replace(",", ".")) if m else None


def promedio_periodo(desde: date, hasta: date, bajar=promedio_publicado) -> Decimal | None:
    """INMAG oficial del período. Se fija una vez pasados unos días, por si faltaba publicar el último remate."""
    r = fetch_one("SELECT CAST(Promedio AS varchar(30)) p FROM dbo.IndiceINMAGPeriodo WHERE Desde=? AND Hasta=?",
                  (desde.isoformat(), hasta.isoformat()))
    if r:
        return Decimal(r["p"])
    try:
        valor = bajar(desde, hasta)
    except OSError:
        return None
    if valor and date.today() >= hasta + timedelta(days=DIAS_PARA_FIJAR):
        execute_write_transaction([("INSERT INTO dbo.IndiceINMAGPeriodo (Desde, Hasta, Promedio, Fuente) VALUES (?,?,?,?)",
                                    (desde.isoformat(), hasta.isoformat(), str(valor), URL))])
    return valor


def descargar(desde: date, hasta: date) -> list[tuple[date, int, Decimal | None]]:
    out = []
    ini = desde
    while ini <= hasta:
        fin = min(date(ini.year, 12, 31), hasta)
        out += parsear(_pedir(ini, fin))
        ini = fin + timedelta(days=1)
    return out


def actualizar(desde: date | None = None, hasta: date | None = None, bajar=descargar) -> dict:
    """Agrega los días faltantes (idempotente). Por defecto, los últimos 10 días."""
    hasta = hasta or date.today()
    desde = desde or hasta - timedelta(days=10)
    filas = bajar(desde, hasta)
    existentes = {r["Fecha"] for r in fetch_all(
        "SELECT CONVERT(varchar(10), Fecha, 23) Fecha FROM dbo.IndiceINMAG WHERE Fecha BETWEEN ? AND ?",
        (desde.isoformat(), hasta.isoformat()))}
    nuevas = [f for f in filas if f[2] is not None and f[0].isoformat() not in existentes]
    if nuevas:
        execute_write_transaction([
            ("INSERT INTO dbo.IndiceINMAG (Fecha, Indice, CabIngresadas, Origen, Fuente) VALUES (?,?,?,'auto',?)",
             (f.isoformat(), str(v), c, URL)) for f, c, v in nuevas])
    return {"agregados": len(nuevas), "sinIndice": [f.isoformat() for f, _, v in filas if v is None],
            "desde": desde.isoformat(), "hasta": hasta.isoformat()}


def listar(desde: date, hasta: date) -> list[dict]:
    return fetch_all(
        "SELECT CONVERT(varchar(10), Fecha, 23) fecha, CAST(Indice AS varchar(30)) indice, CabIngresadas cabIngresadas, "
        "Origen origen, Nota nota FROM dbo.IndiceINMAG WHERE Fecha BETWEEN ? AND ? ORDER BY Fecha",
        (desde.isoformat(), hasta.isoformat()))


def indices(desde: date, hasta: date) -> dict[date, Decimal]:
    return {date.fromisoformat(r["fecha"]): Decimal(r["indice"]) for r in listar(desde, hasta)}


def corregir(fecha: date, indice: Decimal, nota: str, usuario: str) -> dict:
    if indice <= 0:
        raise ValueError("El índice debe ser mayor que cero.")
    if not (nota or "").strip():
        raise ValueError("La carga o corrección manual requiere una nota.")
    previo = fetch_one("SELECT CAST(Indice AS varchar(30)) i FROM dbo.IndiceINMAG WHERE Fecha=?", (fecha.isoformat(),))
    stmts = [("INSERT INTO dbo.IndiceINMAG_Historial (Fecha, IndiceAnterior, IndiceNuevo, Motivo, Usuario) VALUES (?,?,?,?,?)",
              (fecha.isoformat(), previo["i"] if previo else None, str(indice), nota.strip(), usuario))]
    if previo:
        stmts.append(("UPDATE dbo.IndiceINMAG SET Indice=?, Origen='manual', Nota=?, ObtenidoEn=SYSDATETIME() WHERE Fecha=?",
                      (str(indice), nota.strip(), fecha.isoformat())))
    else:
        stmts.append(("INSERT INTO dbo.IndiceINMAG (Fecha, Indice, Origen, Fuente, Nota) VALUES (?,?,'manual','carga manual',?)",
                      (fecha.isoformat(), str(indice), nota.strip())))
    execute_write_transaction(stmts)
    return {"fecha": fecha.isoformat(), "indice": str(indice), "anterior": previo["i"] if previo else None}
