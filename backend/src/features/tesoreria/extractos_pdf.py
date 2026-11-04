"""Importa extractos bancarios nuevos con detección de duplicados robusta (2026-10-01).

- **BNA**: PDF mensuales de "Dropbox/Giamigli de Bolivar SA/Bancos/BNA/Extractos/<año>/".
  Cada renglón trae fecha, concepto, comprobante, importe y saldo. El signo
  sale de la variación del saldo.
- **Galicia**: los PDF mensuales "Dropbox/Giamigli de Bolivar SA/Bancos/Galicia/Extractos/<año>/
  Extracto_Cuentas_Galicia_<fecha>.pdf" (desde 04/11/2026); si no hay PDF nuevo, el Excel
  "Extracto_CC79883834.xlsx" con el parser de tesorería. Las leyendas traen el nombre y el CUIT del destinatario.

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

def _lineas(pdf: Path | bytes) -> list[str]:
    import io

    with pdfplumber.open(io.BytesIO(pdf) if isinstance(pdf, bytes) else pdf) as p:
        return [l.strip() for pg in p.pages for l in (pg.extract_text() or "").splitlines() if l.strip()]


def leer_bna(desde: date) -> list[dict]:
    movimientos = []
    for pdf in sorted(CARPETA_BNA.glob("*/Extracto *.pdf")):
        movimientos += leer_bna_pdf(_lineas(pdf), pdf.name, desde)
    return movimientos


def leer_bna_pdf(lineas: list[str], nombre: str, desde: date | None = None) -> list[dict]:
    movimientos = []
    if True:
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
            if desde is not None and fecha < desde:
                continue
            movimientos.append({"fecha": fecha, "concepto": m.group(2).strip(), "comprobante": m.group(3),
                                "importe": round(signo * importe, 2), "saldo": nuevo_saldo, "archivo": nombre})
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

CARPETA_GALICIA_PDF = Path(r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Bancos\Galicia\Extractos")
_MOV_GAL = re.compile(r"^(\d{2}/\d{2}/\d{2}) (.+?) (-?[\d.]+,\d{2}) (-?[\d.]+,\d{2})$")
_RUIDO_GAL = re.compile(r"^(Resumen de Cuenta|Fecha Descripci|\d{8}\d+[A-Z]$|Movimientos$|.*P.gina \d+ / \d+)")
_FIN_GAL = re.compile(r"^(Total|Saldo|Detalle|Impuesto|Retenci|Percepci|Los dep|Para |Consult)")
_FECHA_PDF = re.compile(r"(\d{4})_(\d{2})_(\d{2})")


def leer_galicia_pdf(pdf: Path | bytes, nombre: str | None = None) -> list[dict]:
    """Movimientos del resumen PDF de Galicia. Cada renglón: fecha, descripción [origen], importe con signo, saldo;
    las líneas siguientes hasta el próximo renglón son leyendas (destinatario, CUIT, referencia). Verifica la cadena
    de saldos de punta a punta: si un renglón no cierra, no se carga nada."""
    lineas = _lineas(pdf)
    nombre = nombre or getattr(pdf, "name", "extracto")
    m_ant = re.search(r"Saldos\s.*?\$([\d.]+,\d{2})", "\n".join(lineas), re.S)
    movs: list[dict] = []
    fin = False
    for l in lineas:
        m = _MOV_GAL.match(l)
        if m:
            fin = False
            imp, saldo = _num(m.group(3)), _num(m.group(4))
            movs.append({"fecha": datetime.strptime(m.group(1), "%d/%m/%y").date(),
                         "descripcion": re.sub(r"\s+\d{4}$", "", m.group(2)).strip(),  # sin el "Origen" (0001)
                         "debitos": -imp if imp < 0 else None, "creditos": imp if imp > 0 else None,
                         "saldo": saldo, "importe": imp, "leyendas": [], "numeroComprobante": None})
        elif movs and not fin and not _RUIDO_GAL.match(l):
            if _FIN_GAL.match(l):
                fin = True
                continue
            mv = movs[-1]
            if not mv["leyendas"] and re.search(r"\b(DE|DEL|A|EN)$", mv["descripcion"]):
                mv["descripcion"] += " " + l  # descripción partida en dos líneas ("ACREDITAMIENTO DE / HABERES")
            else:
                mv["leyendas"].append(l)
    if not movs:
        return []
    saldo = _num(m_ant.group(1)) if m_ant else round(movs[0]["saldo"] - movs[0]["importe"], 2)
    for mv in movs:
        saldo = round(saldo + mv["importe"], 2)
        if abs(saldo - mv["saldo"]) > 0.009:
            raise RuntimeError(f"{nombre}: el saldo no cierra en {mv['fecha']:%d/%m} {mv['descripcion']} "
                               f"({saldo:,.2f} calculado vs {mv['saldo']:,.2f} del banco)")
    for mv in movs:
        mv["descripcion"] = mv["descripcion"].title()  # mismo estilo que las cargas desde el Excel
        if len(mv["leyendas"]) > 4:
            mv["leyendas"] = mv["leyendas"][:3] + [" ".join(mv["leyendas"][3:])]
    return movs


def leer_galicia() -> list[dict]:
    """PDF de los meses que todavía no están completos en la base; si no hay, el Excel."""
    ultimo = fetch_all("SELECT MAX(Fecha) AS f FROM dbo.[Movimientos Galicia]")[0]["f"]
    pdfs = []
    for f in sorted(CARPETA_GALICIA_PDF.glob("*/Extracto_Cuentas_Galicia_*.pdf")):
        m = _FECHA_PDF.search(f.name)
        if m and (ultimo is None or date(*map(int, m.groups())) > ultimo.date()):
            pdfs.append(f)
    if pdfs:
        print("Galicia desde PDF: " + ", ".join(f.name for f in pdfs))
        return [m for f in pdfs for m in leer_galicia_pdf(f)]
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
    # eCheq 125 a Ricardo Criado: componente impositivo del balance 25-26 (Ganancias + IIBB + IVA), 03/11/2026.
    ({"fecha": date(2026, 10, 9), "debitos": 884932.61}, 210, "eCheq 125 del balance 25-26 de Criado"),
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


def asignar_bna(bna: list[dict]) -> list[dict]:
    hist = historial("Movimientos BNA", "Concepto", "[Fecha / Hora Mov#]")
    for m in bna:
        explicita = regla_explicita(m["concepto"], [], m)
        if explicita:
            m["idContacto"], m["regla"] = explicita
        elif _norm(m["concepto"]) in hist:
            m["idContacto"], m["regla"] = hist[_norm(m["concepto"])], "historial"
        else:
            m["idContacto"], m["regla"] = None, "sin asignar"
    return bna


def asignar_galicia(gal: list[dict]) -> list[dict]:
    hist = historial("Movimientos Galicia", "[Descripción]", "Fecha")
    por_cuit = contactos_por_cuit()
    for m in gal:
        cuits = [re.sub(r"\D", "", str(x)) for x in (m.get("leyendas") or [])
                 if x and re.fullmatch(r"\d{11}", re.sub(r"\D", "", str(x)))]
        cuit = next((c for c in cuits if c not in CUIT_PROPIO and c in por_cuit), None)
        explicita = regla_explicita(m["descripcion"], m.get("leyendas") or [], m)
        if explicita:
            m["idContacto"], m["regla"] = explicita
        elif cuit:
            m["idContacto"], m["regla"] = por_cuit[cuit], f"CUIT {cuit}"
        elif _norm(m["descripcion"]) in hist:
            m["idContacto"], m["regla"] = hist[_norm(m["descripcion"])], "historial"
        else:
            m["idContacto"], m["regla"] = None, "sin asignar"
    return gal


def grabar(bna: list[dict], gal: list[dict], motivo: str = "extractos-bancarios") -> None:
    from src.features.vinculos.backup import backup_verificado

    if not bna and not gal:
        return
    backup_verificado(motivo)
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
    execute_write_transaction(stmts)


# --- PDF subido desde la pantalla (04/11/2026) ----------------------------------

def detectar_banco(lineas: list[str]) -> str | None:
    texto = "\n".join(lineas[:60]).upper()
    if "RESUMEN DE CUENTA CORRIENTE" in texto and ("0070383" in texto or "GALICIA" in texto):
        return "galicia"
    if any(l.startswith("SALDO ANTERIOR") for l in lineas):
        return "bna"
    return None


def _analizar(nombre: str, contenido: bytes) -> tuple[str, list[dict], int]:
    """(banco, movimientos nuevos con contacto propuesto, cantidad ya cargada). No escribe nada."""
    lineas = _lineas(contenido)
    banco = detectar_banco(lineas)
    hoy = date.today()
    if banco == "galicia":
        todos = leer_galicia_pdf(contenido, nombre)
        nuevos = asignar_galicia([m for m in nuevos_galicia(todos) if m["fecha"] < hoy])
    elif banco == "bna":
        todos = leer_bna_pdf(lineas, nombre)
        nuevos = asignar_bna([m for m in nuevos_bna(todos) if m["fecha"] < hoy])
    else:
        raise ValueError(["No se reconoce el extracto: por ahora se leen los resúmenes PDF de Galicia y del BNA."])
    if not todos:
        raise ValueError(["No se encontraron movimientos en el extracto."])
    _marcar_canjes(banco, nuevos)
    return banco, nuevos, len(todos) - len(nuevos)


# --- Canjes de socio pendientes (04/11/2026) ------------------------------------
# Un socio deja efectivo en la caja y la empresa le transfiere lo mismo: el canje se registra en la caja con la
# transferencia "pendiente" hasta que llega el resumen. Al cargarlo, la transferencia que coincide en banco, fecha e
# importe va al contacto de socio (no al CUIT, que puede ser el contacto de empleado) y se vincula sola al canje.

def canjes_pendientes(banco: str) -> list[dict]:
    from src.features.cuentas_socios.contactos import SOCIO_CONTACTO

    filas = fetch_all(
        "SELECT o.IdOperacion AS id, o.Fecha AS fecha, o.IdSocio AS socio, o.Version AS version, "
        "JSON_VALUE(o.Solicitud,'$.importe') AS importe FROM dbo.OperacionesCajaEfectivo o "
        "WHERE o.Estado = 'Vigente' AND o.Tipo = 'canje_socio' AND JSON_VALUE(o.Solicitud,'$.bancoPendiente') = ? "
        "AND NOT EXISTS (SELECT 1 FROM dbo.BancoOperacionCaja b WHERE b.IdOperacion = o.IdOperacion)", (banco,))
    return [{**f, "importe": round(float(f["importe"]), 2), "fecha": f["fecha"] if isinstance(f["fecha"], date)
             else date.fromisoformat(str(f["fecha"])[:10]), "contacto": SOCIO_CONTACTO.get(f["socio"])} for f in filas]


def _salida_de(banco: str, m: dict) -> float:
    return round(-m["importe"] if banco == "bna" else (m.get("debitos") or 0), 2)


def _marcar_canjes(banco: str, nuevos: list[dict]) -> None:
    for c in canjes_pendientes(banco):
        candidatos = [m for m in nuevos if m["fecha"] == c["fecha"] and _salida_de(banco, m) == c["importe"]
                      and not m.get("canje")]
        if len(candidatos) == 1 and c["contacto"]:
            m = candidatos[0]
            m["idContacto"], m["regla"], m["canje"] = c["contacto"], f"canje de socio (operación {c['id']})", c
        # 0 o varios candidatos: queda para vincular a mano desde la caja.


def _vincular_canjes(banco: str, nuevos: list[dict]) -> int:
    from src.features.cajas_efectivo import service
    from src.features.cajas_efectivo.schemas import ConciliarBancoCaja

    hechos = 0
    for m in (x for x in nuevos if x.get("canje")):
        if banco == "galicia":
            fila = fetch_all("SELECT TOP 1 IdMovimiento AS id FROM dbo.[Movimientos Galicia] WHERE Fecha = ? AND [Débitos] = ? "
                             "AND Saldo = ? ORDER BY IdMovimiento DESC", (m["fecha"], m["debitos"], m["saldo"]))
        else:
            fila = fetch_all("SELECT TOP 1 IdMovimientoBNA AS id FROM dbo.[Movimientos BNA] WHERE [Fecha / Hora Mov#] = ? "
                             "AND Importe = ? AND IdCuentaBancaria = ? ORDER BY IdMovimientoBNA DESC",
                             (m["fecha"], m["importe"], ID_CUENTA_BNA))
        if not fila:
            continue
        try:
            service.conciliar_banco(m["canje"]["id"], ConciliarBancoCaja.model_validate(
                {"banco": {"medio": banco, "idMovimiento": fila[0]["id"]}, "versionEsperada": m["canje"]["version"]}),
                "carga de extracto")
            hechos += 1
        except Exception:  # se puede vincular a mano desde la caja; la carga no se frena por esto
            pass
    return hechos


def _salida(banco: str, nuevos: list[dict], ya: int) -> dict:
    nom = nombres()
    movs = []
    for m in nuevos:
        imp = m["importe"] if banco == "bna" else (m.get("creditos") or 0) - (m.get("debitos") or 0)
        movs.append({
            "fecha": m["fecha"].isoformat(), "descripcion": m.get("concepto") or m.get("descripcion"),
            "importe": round(imp, 2), "saldo": m.get("saldo"),
            "contacto": nom.get(m["idContacto"]) if m["idContacto"] else None,
            "sinContacto": m["idContacto"] is None,
            "detalle": " · ".join(str(x) for x in (m.get("leyendas") or []) if x)[:120] or None,
        })
    return {"banco": "Galicia" if banco == "galicia" else "Banco Nación", "nuevos": movs, "yaCargados": ya}


def _leer(nombre: str, contenido: bytes) -> tuple[str, list[dict], int]:
    try:
        return _analizar(nombre, contenido)
    except RuntimeError as e:  # la cadena de saldos no cierra: no se carga nada
        raise ValueError([f"El extracto no se pudo leer bien ({e}). No se cargó nada."]) from e


def previsualizar(nombre: str, contenido: bytes) -> dict:
    return _salida(*_leer(nombre, contenido))


def confirmar(nombre: str, contenido: bytes) -> dict:
    banco, nuevos, ya = _leer(nombre, contenido)
    if banco == "galicia":
        grabar([], nuevos, "extracto-pdf-galicia")
    else:
        grabar(nuevos, [], "extracto-pdf-bna")
    vinculados = _vincular_canjes(banco, nuevos)
    _guardar_copia(banco, nombre, contenido)
    return {**_salida(banco, nuevos, ya), "grabados": len(nuevos), "canjesVinculados": vinculados}


def _guardar_copia(banco: str, nombre: str, contenido: bytes) -> None:
    """Deja el PDF en la carpeta de extractos del banco (si no estaba), junto con los demás."""
    carpeta = (CARPETA_GALICIA_PDF if banco == "galicia" else CARPETA_BNA) / str(date.today().year)
    try:
        carpeta.mkdir(parents=True, exist_ok=True)
        if any(f.stat().st_size == len(contenido) and f.read_bytes() == contenido for f in carpeta.glob("*.pdf")):
            return
        destino, n = carpeta / Path(nombre).name, 1
        while destino.exists():
            destino, n = carpeta / f"{Path(nombre).stem} {n:03d}.pdf", n + 1
        destino.write_bytes(contenido)
    except OSError:
        pass  # la carga ya quedó hecha; la copia es solo para el archivo


def main(aplicar: bool) -> None:
    hoy = date.today()
    nom = nombres()
    ultimo_bna = fetch_all("SELECT MAX([Fecha / Hora Mov#]) AS f FROM dbo.[Movimientos BNA] WHERE IdCuentaBancaria = ?",
                           (ID_CUENTA_BNA,))[0]["f"].date()
    bna = asignar_bna([m for m in nuevos_bna(leer_bna(ultimo_bna - timedelta(days=31))) if m["fecha"] < hoy])
    gal = asignar_galicia([m for m in nuevos_galicia(leer_galicia()) if m["fecha"] < hoy])

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
    grabar(bna, gal)
    print(f"Grabado: {len(bna)} movimientos BNA y {len(gal)} Galicia.")


if __name__ == "__main__":
    import sys

    main(aplicar="--aplicar" in sys.argv)
