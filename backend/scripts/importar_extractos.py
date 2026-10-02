"""Importa extractos bancarios nuevos con detección de duplicados robusta (2026-10-01).

- **BNA**: PDF mensuales de "Dropbox/Giamigli de Bolivar SA/Bancos/BNA/Extractos/<año>/".
  Cada renglón trae fecha, concepto, comprobante, importe y saldo. El signo
  sale de la variación del saldo.
- **Galicia**: el Excel "Extracto_CC79883834.xlsx", con el parser existente
  de tesorería. Sus leyendas traen el nombre y el CUIT del destinatario.

Duplicados: el importador de 013 compara el comprobante y los débitos tal
como vienen. La base guardó vacíos los comprobantes y los débitos en cero,
así que esa comparación falla y duplica. Este script usa claves que
coinciden en los dos lados:

- **BNA**: (fecha, importe con signo, comprobante, concepto).
- **Galicia**: (fecha, débito, crédito, saldo). El saldo del banco después de
  cada movimiento identifica el renglón.

Contacto propuesto para cada movimiento nuevo, en este orden:

1. **CUIT de la leyenda** (Galicia), buscado en Contactos.
2. **Historial del concepto**: el contacto que tuvo ese mismo concepto en
   el 90% o más de los movimientos de los últimos 2 años (mínimo 3).
3. **Sin asignar**: queda listado para revisar.

No se cargan los movimientos de hoy, porque el día todavía no cerró.

Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.importar_extractos [--aplicar]
"""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import pdfplumber

from src.db.connection import execute_write_transaction, fetch_all
from src.features.tesoreria import confirmacion_carga, excel_import

CARPETA_BNA = Path(r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Bancos\BNA\Extractos")
ARCHIVO_GALICIA = Path(r"C:\Users\Sergio\Documents\La Herencia\Bancos y finanzas\Galicia\Extracto_CC79883834.xlsx")
ID_CUENTA_BNA = 3  # 6150111899, sucursal General Pacheco (la vigente)
CUIT_PROPIO = {"30712114602"}

_RENGLON = re.compile(r"^(\d{2}/\d{2}/\d{2})\s+(.+?)\s+(\d+)?\s*([\d\.]+,\d{2})\s+(-?[\d\.]+,\d{2})$")


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().upper()


# --- BNA ---------------------------------------------------------------------

def leer_bna(desde: date) -> list[dict]:
    movimientos = []
    for pdf in sorted(CARPETA_BNA.glob("*/Extracto *.pdf")):
        with pdfplumber.open(pdf) as p:
            lineas = "\n".join(pg.extract_text() or "" for pg in p.pages).splitlines()
        saldo = None
        for linea in lineas:
            linea = linea.strip()
            if linea.startswith("SALDO ANTERIOR"):
                saldo = _num(linea.split()[-1])
                continue
            m = _RENGLON.match(linea)
            if not m or saldo is None:
                continue
            fecha = datetime.strptime(m.group(1), "%d/%m/%y").date()
            importe, nuevo_saldo = _num(m.group(4)), _num(m.group(5))
            signo = 1 if nuevo_saldo > saldo else -1
            saldo = nuevo_saldo
            if fecha < desde:
                continue
            movimientos.append({"fecha": fecha, "concepto": m.group(2).strip(), "comprobante": m.group(3),
                                "importe": round(signo * importe, 2), "saldo": nuevo_saldo, "archivo": pdf.name})
    return movimientos


def nuevos_bna(movimientos: list[dict]) -> list[dict]:
    if not movimientos:
        return []
    desde = min(m["fecha"] for m in movimientos)
    existentes = Counter(
        (f["fecha"].date(), round(float(f["importe"]), 2), confirmacion_carga._norm_comprobante(f["c"]), _norm(f["concepto"]))
        for f in fetch_all("SELECT [Fecha / Hora Mov#] AS fecha, Importe AS importe, [Nro# Comprobante] AS c, "
                           "Concepto AS concepto FROM dbo.[Movimientos BNA] WHERE [Fecha / Hora Mov#] >= ?", (desde,)))
    nuevos = []
    for m in movimientos:
        clave = (m["fecha"], m["importe"], confirmacion_carga._norm_comprobante(m["comprobante"]), _norm(m["concepto"]))
        if existentes[clave] > 0:
            existentes[clave] -= 1  # mismo renglón ya cargado (tolera renglones idénticos repetidos)
        else:
            nuevos.append(m)
    return nuevos


# --- Galicia -----------------------------------------------------------------

def leer_galicia() -> list[dict]:
    p = excel_import.validar_y_previsualizar(ARCHIVO_GALICIA.name, ARCHIVO_GALICIA.read_bytes())
    if not p["valido"]:
        raise RuntimeError(p["errores"])
    return p["movimientosPrevisualizados"]


def nuevos_galicia(movimientos: list[dict]) -> list[dict]:
    if not movimientos:
        return []
    desde = min(m["fecha"] for m in movimientos)
    def clave(fecha, deb, cre, saldo):
        return (fecha, round(float(deb or 0), 2), round(float(cre or 0), 2), round(float(saldo or 0), 2))
    existentes = Counter(clave(f["fecha"].date(), f["deb"], f["cre"], f["saldo"]) for f in fetch_all(
        "SELECT Fecha AS fecha, [Débitos] AS deb, [Créditos] AS cre, Saldo AS saldo FROM dbo.[Movimientos Galicia] "
        "WHERE Fecha >= ?", (desde,)))
    nuevos = []
    for m in movimientos:
        k = clave(m["fecha"], m.get("debitos"), m.get("creditos"), m.get("saldo"))
        if existentes[k] > 0:
            existentes[k] -= 1
        else:
            nuevos.append(m)
    return nuevos


# --- Contactos ---------------------------------------------------------------

def contactos_por_cuit() -> dict[str, int]:
    return {re.sub(r"\D", "", str(f["cuit"])): f["id"] for f in fetch_all(
        "SELECT IdContacto AS id, [CUIT/CUIL] AS cuit FROM dbo.Contactos WHERE [CUIT/CUIL] IS NOT NULL")
        if re.sub(r"\D", "", str(f["cuit"]))}


def historial(tabla: str, col_concepto: str, col_fecha: str) -> dict[str, int | None]:
    """Concepto → contacto, si el concepto tuvo siempre (≥90%) el mismo contacto."""
    desde = date.today() - timedelta(days=730)
    por_concepto: dict[str, Counter] = defaultdict(Counter)
    for f in fetch_all(f"SELECT {col_concepto} AS c, IdContacto AS id FROM dbo.[{tabla}] WHERE {col_fecha} >= ?", (desde,)):
        por_concepto[_norm(f["c"])][f["id"]] += 1
    resultado = {}
    for concepto, cnt in por_concepto.items():
        total = sum(cnt.values())
        contacto, n = cnt.most_common(1)[0]
        if total >= 3 and n / total >= 0.9:
            resultado[concepto] = contacto
    return resultado


def nombres() -> dict[int, str]:
    return {f["id"]: f["n"] for f in fetch_all("SELECT IdContacto AS id, [Razon Social] AS n FROM dbo.Contactos")}


# Reglas explícitas, verificadas contra el historial el 2026-10-01. Se
# aplican antes que el historial. El contacto 0 es la convención para el
# impuesto al débito y crédito.
REGLAS_CONCEPTO = [
    (r"^(IMP\. DEB\. LEY 25413|IMP\. CRE\. LEY 25413|GRAVAMEN LEY 25413)", 0),
    (r"^RESCATE FIMA", 518),           # fondo FIMA de Banco Galicia
    (r"^IVA$", 518),
    (r"^DEBITO AUTOMATICO GALICIA", 518),
]
REGLAS_LEYENDA = [  # (concepto, palabra en la leyenda, contacto)
    (r"^PAGO DE SERVICIOS", r"^ARBA", 12),
    (r"^PAGO DE SERVICIOS", r"^COOP BOLIVAR", 23),
    (r"^PAGO DE SERVICIOS", r"^BOLIVAR$", 72),
    (r"^PAGO DE SERVICIOS", r"^SANCOR", 171),
    (r"^PAGO DE SERVICIOS", r"^MOVISTAR", 71),
    (r"^DEB\. AUTOM\. DE SERV\.", r"^ALLIANZ", 515),
    (r"^DEB\. AUTOM\. DE SERV\.", r"^AFIP", 119),
    (r"^DEB\. AUTOM\. DE SERV\.", r"^SENASA", 250),
    (r"^TRF INMED PROVEED", r"^HONORAR", 115),  # Criado, Ricardo Marcos: honorarios de Estudio Criado
]
# Casos puntuales con respaldo documental.
REGLAS_PUNTUALES = [
    # Pago de la factura 00001-00000327 de Aguilar, Gabriel ($574.600 menos retención
    # $9.056,60, "Detalle de Pagos.xlsx"), transferido a la cuenta de Luz Eugenia Soledad Mori.
    ({"fecha": date(2026, 9, 23), "debitos": 565543.40}, 634, "Detalle de Pagos: factura 00001-00000327 de Aguilar"),
]


def regla_explicita(concepto: str, leyendas: list, mov: dict) -> tuple[int | None, str] | None:
    for cond, contacto, motivo in REGLAS_PUNTUALES:
        if all(round(float(mov.get(k) or 0), 2) == v if isinstance(v, float) else mov.get(k) == v
               for k, v in cond.items()):
            return contacto, motivo
    c = _norm(concepto)
    for patron, contacto in REGLAS_CONCEPTO:
        if re.search(patron, c):
            return contacto, "regla de concepto"
    leyendas_norm = [_norm(x) for x in leyendas if x]
    for patron_c, patron_l, contacto in REGLAS_LEYENDA:
        if re.search(patron_c, c) and any(re.search(patron_l, l) for l in leyendas_norm):
            return contacto, "regla de leyenda"
    return None


def main(aplicar: bool) -> None:
    hoy = date.today()
    nom = nombres()
    por_cuit = contactos_por_cuit()

    ultimo_bna = fetch_all("SELECT MAX([Fecha / Hora Mov#]) AS f FROM dbo.[Movimientos BNA] WHERE IdCuentaBancaria = ?",
                           (ID_CUENTA_BNA,))[0]["f"].date()
    bna = [m for m in nuevos_bna(leer_bna(ultimo_bna - timedelta(days=31))) if m["fecha"] < hoy]
    hist_bna = historial("Movimientos BNA", "Concepto", "[Fecha / Hora Mov#]")
    for m in bna:
        explicita = regla_explicita(m["concepto"], [], m)
        if explicita:
            m["idContacto"], m["regla"] = explicita
        elif _norm(m["concepto"]) in hist_bna:
            m["idContacto"], m["regla"] = hist_bna[_norm(m["concepto"])], "historial"
        else:
            m["idContacto"], m["regla"] = None, "sin asignar"

    gal = [m for m in nuevos_galicia(leer_galicia()) if m["fecha"] < hoy]
    hist_gal = historial("Movimientos Galicia", "[Descripción]", "Fecha")
    for m in gal:
        cuits = [re.sub(r"\D", "", str(x)) for x in (m.get("leyendas") or []) if x and re.fullmatch(r"\d{11}", re.sub(r"\D", "", str(x)))]
        cuit = next((c for c in cuits if c not in CUIT_PROPIO and c in por_cuit), None)
        explicita = regla_explicita(m["descripcion"], m.get("leyendas") or [], m)
        if explicita:
            m["idContacto"], m["regla"] = explicita
        elif cuit:
            m["idContacto"], m["regla"] = por_cuit[cuit], f"CUIT {cuit}"
        elif _norm(m["descripcion"]) in hist_gal:
            m["idContacto"], m["regla"] = hist_gal[_norm(m["descripcion"])], "historial"
        else:
            m["idContacto"], m["regla"] = None, "sin asignar"

    print(f"BNA: {len(bna)} movimientos nuevos (cuenta 6150111899).")
    for m in bna:
        quien = nom.get(m["idContacto"], "—") if m["idContacto"] is not None else "SIN ASIGNAR"
        print(f"  {m['fecha']:%d/%m/%Y} {m['concepto'][:30]:30} {m['importe']:>15,.2f}  {quien[:28]:28} ({m['regla']})")
    print(f"Galicia: {len(gal)} movimientos nuevos.")
    for m in gal:
        imp = (m.get("creditos") or 0) - (m.get("debitos") or 0)
        quien = nom.get(m["idContacto"], "—") if m["idContacto"] is not None else "SIN ASIGNAR"
        ley = " | ".join(str(x) for x in (m.get("leyendas") or []) if x)[:45]
        print(f"  {m['fecha']:%d/%m/%Y} {m['descripcion'][:26]:26} {imp:>15,.2f}  {quien[:26]:26} ({m['regla']})  {ley}")

    if not aplicar:
        print("Simulación: no se escribió nada. Usar --aplicar para grabar.")
        return
    from src.features.vinculos.backup import backup_verificado
    print(f"Respaldo verificado: {backup_verificado('extractos-bancarios')}")
    stmts = []
    for m in bna:
        stmts.append(("INSERT INTO dbo.[Movimientos BNA] ([Fecha / Hora Mov#], [Nro# Comprobante], Concepto, Importe, "
                      "IdContacto, IdCuentaBancaria) VALUES (?, ?, ?, ?, ?, ?)",
                      (m["fecha"], float(m["comprobante"]) if m["comprobante"] else None, m["concepto"], m["importe"],
                       m["idContacto"], ID_CUENTA_BNA)))
    for m in gal:
        stmts.append(("INSERT INTO dbo.[Movimientos Galicia] (Fecha, [Descripción], [Débitos], [Créditos], "
                      "[Número de Comprobante], Saldo, IdContacto) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (m["fecha"], m["descripcion"], m.get("debitos") or None, m.get("creditos") or None,
                       confirmacion_carga._to_float_or_none(m.get("numeroComprobante")), m.get("saldo"), m["idContacto"])))
    if stmts:
        execute_write_transaction(stmts)
    print(f"Grabado: {len(bna)} movimientos BNA y {len(gal)} Galicia.")


if __name__ == "__main__":
    main(aplicar="--aplicar" in sys.argv)
