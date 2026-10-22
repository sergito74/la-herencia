"""039: índice INMAG diario (Mercado Agroganadero de Cañuelas, haciinfo000011).

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

URL = "https://www.mercadoagroganadero.com.ar/dll/hacienda2.dll/haciinfo000011"
_FILA = re.compile(
    r'<TD Align="Center">\w\w&nbsp;(\d\d/\d\d/\d{4})</TD><TD Align="Right">([^<]*)</TD>'
    r'<TD Align="Right">[^<]*</TD><TD Align="Center">([^<]*)</TD>'
)


def parsear(html: str) -> list[tuple[date, int, Decimal | None]]:
    out = []
    for f, cab, ind in _FILA.findall(html):
        ind = ind.replace("*", "").strip()
        valor = Decimal(ind.replace(".", "").replace(",", ".")) if re.fullmatch(r"[\d.]+,\d+", ind) else None
        cab = cab.strip().replace(".", "")
        out.append((datetime.strptime(f, "%d/%m/%Y").date(), int(cab) if cab.isdigit() else 0, valor if valor else None))
    return out


def descargar(desde: date, hasta: date) -> list[tuple[date, int, Decimal | None]]:
    out = []
    ini = desde
    while ini <= hasta:
        fin = min(date(ini.year, 12, 31), hasta)
        datos = urllib.parse.urlencode({
            "ID": "", "CP": "", "FLASH": "", "USUARIO": "SIN IDENTIFICAR", "OPCIONMENU": "", "OPCIONSUBMENU": "",
            "txtFechaIni": ini.strftime("%d/%m/%Y"), "txtFechaFin": fin.strftime("%d/%m/%Y"),
        }).encode()
        req = urllib.request.Request(URL, data=datos, headers={"User-Agent": "Mozilla/5.0"})
        out += parsear(urllib.request.urlopen(req, timeout=120).read().decode("latin-1"))
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
