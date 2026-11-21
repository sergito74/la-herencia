"""Auditoría histórica del vínculo remito ↔ factura (solo lectura; re-corrible).

Objetivo (Sergio 21/11/2026): toda entrada al stock tiene que estar vinculada, directa o indirectamente, a una
factura; un remito mal vinculado desplaza el FIFO y el costo real de los cultivos.

Recalcula desde cero el emparejamiento de TODOS los renglones de remito con los renglones de factura y lo compara
con `tblRemitoCompra`:
  · mismo proveedor;
  · producto por el TEXTO del renglón de factura (nombre o principio activo del producto del remito) o por el mismo
    IdFormulado. No se confía en el IdFormulado de la factura: muchos tienen códigos genéricos (CURASEM, TRIBU, 0);
  · cantidad exacta (±1%), con uno o varios renglones de la misma factura (Sergio parte cada producto por cultivo),
    o con hasta 3 facturas;
  · factura hasta VENTANA días antes o después del remito, la más cercana en fecha;
  · en orden cronológico de remitos; cada renglón de factura se consume una sola vez.
Salida: Excel con el estado de cada renglón de remito (OK / NUEVO / CAMBIO / REVISAR) y los renglones de factura
cuyo producto hay que corregir.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import fetch_all  # noqa: E402
from src.features.remitos.stock_datos import equivalencias, factor_a_base, unidades_base  # noqa: E402

VENTANA = 270
TOL = 0.01
EPS = 1e-6
GENERICOS = {"LTS", "LITROS", "LITRO", "KGS", "KG", "KILOS", "BOLSA", "BOLSAS", "CURASEMILLA", "CURASEMILLAS", "SEMILLA",
             "SEMILLAS", "BIDON", "PLUS", "FORRAJERO", "GRANERO", "SISTEMIC", "SYSTEMIC", "SIST", "EBC", "WG", "SC", "EC",
             "SL", "FS", "WP", "SG", "OD", "LT", "CON", "PARA", "DEL", "LOS", "LAS", "SUSP", "CONC", "MAS", "TEQ",
             "GRANEL", "GRANULADA", "MATERIA", "PRIMA", "TONELADAS", "SEMILLAS"}


def norm(t) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().upper()
    return " ".join(re.sub(r"[^A-Z0-9%]+", " ", t).split())


def tokens(t) -> set[str]:
    """Raíces de 7 letras (METRIBUZIN = METRIBUZINA, CARBENDAZIM = CARBENDAZIMA)."""
    t = norm(t)
    out = {w[:7] for w in t.split() if len(w) >= 4 and w not in GENERICOS and not (w.isdigit() and len(w) > 5)}
    # códigos de híbrido/variedad pegados al nombre (NS7818VIP3, AX7761VT3)
    out |= {m for m in re.findall(r"(?<!\d)(\d{4,5})(?!\d)", t.replace(" ", " "))}
    return out


def d(v):
    return v.date() if isinstance(v, datetime) else v


def iguales(a, b):
    """±1%; ±2% en cantidades de más de 1.000 (granel en kg: diferencias de balanza)."""
    tol = 0.02 if min(abs(a), abs(b)) > 1000 else TOL
    return abs(a - b) <= tol * max(abs(a), abs(b), 1.0)


def cargar():
    bases, equiv = unidades_base(), equivalencias()
    prod = {int(p["IdProducto"]): p for p in fetch_all("SELECT IdProducto, Producto, TipoProducto, IngredienteActivo FROM dbo.vw_ProductosBase")}
    remitos = fetch_all(
        """
        SELECT rd.IdDetalleRemito AS idR, rd.IdRemito AS idRemito, r.NroRemito AS nro, r.Fecha AS fecha,
               COALESCE(r.IdContacto, r.IdProveedor) AS prov, rd.IdFormulado AS prod, rd.Cantidad AS cant, rd.[Unidad Medida] AS unidad
        FROM dbo.Remitos_Detalles rd JOIN dbo.Remitos r ON r.IdRemito = rd.IdRemito
        LEFT JOIN dbo.Remitos_Extra e ON e.IdRemito = r.IdRemito
        WHERE ISNULL(e.Anulado, 0) = 0 AND rd.IdFormulado IS NOT NULL AND r.Fecha IS NOT NULL AND ISNULL(rd.Cantidad, 0) > 0
        ORDER BY r.Fecha, rd.IdDetalleRemito
        """)
    facturas = fetch_all(
        """
        SELECT dc.IdDetalleCompra AS idC, dc.IdCompra AS idCompra, c.Fecha AS fecha, c.IdContacto AS prov, c.[Nro Documento] AS nro,
               c.[Tipo documento] AS tipo, dc.Cantidad AS cant, dc.Unidad AS unidad, dc.[Producto/Servicio] AS texto,
               NULLIF(dc.IdFormulado, 0) AS prod, dc.[Precio Unitario] AS pu, c.Moneda AS moneda, c.[Tipo de Cambio] AS tc
        FROM dbo.Det_Compras dc JOIN dbo.Compras c ON c.IdDeuda = dc.IdCompra
        WHERE ISNULL(dc.Cantidad, 0) > 0 AND ISNULL(dc.[Precio Unitario], 0) > 0 AND ISNULL(dc.Unidad, '') NOT IN ('ARS', 'USD')
          AND c.[Tipo documento] = 'Factura'
          -- Clasificado NoImputa (p. ej. factura refacturada por NC "cambia cond."): no es entrada de mercadería.
          AND NOT EXISTS (SELECT 1 FROM dbo.TamizRenglones tz WHERE tz.IdDetalleCompra = dc.IdDetalleCompra AND tz.Vigente = 1
                          AND tz.Destino = 'NoImputa')
        """)
    # Factura de ajuste de precio: repite cantidades de una compra con un precio ínfimo (p. ej. Cargill 7028-00066585,
    # arrancador a US$ 0,66/t). Renglón con precio en US$ < 10% de la mediana del producto en ese proveedor → no es entrada.
    def _usd(f):
        tc = float(f["tc"] or 0)
        return float(f["pu"]) if (f["moneda"] or "").startswith("Dol") else (float(f["pu"]) / tc if tc > 1 else None)

    def _grupo(f):
        t = norm(f["texto"])
        return (f["prov"], familia(t) or " ".join(sorted(tokens(t))), bool(re.match(r"^(TON|TN)", t)))
    precios = defaultdict(list)
    for f in facturas:
        if _usd(f):
            precios[_grupo(f)].append(_usd(f))
    mediana = {k: sorted(v)[len(v) // 2] for k, v in precios.items() if len(v) >= 3}
    ajustes = {f["idC"] for f in facturas if _usd(f) and _grupo(f) in mediana and _usd(f) < 0.1 * mediana[_grupo(f)]}
    facturas = [f for f in facturas if f["idC"] not in ajustes]
    # Una NC de devolución (texto 'devoluc') anula el renglón de factura anterior del mismo proveedor, texto y cantidad:
    # esa mercadería no entró (o volvió). Las ND son ajustes de precio/cambio: no son entradas.
    ncs = fetch_all(
        """
        SELECT c.IdContacto AS prov, c.Fecha AS fecha, dc.Cantidad AS cant, dc.[Producto/Servicio] AS texto
        FROM dbo.Det_Compras dc JOIN dbo.Compras c ON c.IdDeuda = dc.IdCompra
        WHERE c.[Tipo documento] LIKE 'Nota de Cr%' AND dc.[Producto/Servicio] LIKE '%devolu%' AND ISNULL(dc.Cantidad, 0) > 0
        """)
    anuladas = set()
    for nc in ncs:
        base_txt = norm(re.sub(r"\(?devoluci\w*\)?", "", nc["texto"], flags=re.I))
        previas = [f for f in facturas if f["prov"] == nc["prov"] and f["idC"] not in anuladas and d(f["fecha"]) <= d(nc["fecha"])
                   and norm(f["texto"]) == base_txt and iguales(float(f["cant"]), float(nc["cant"]))]
        if previas:
            anuladas.add(max(previas, key=lambda f: (f["fecha"], f["idC"]))["idC"])
    facturas = [f for f in facturas if f["idC"] not in anuladas and not re.search(r"\bANULAD", norm(f["texto"]))]
    vinc = fetch_all("SELECT IdDetalleRemito AS idR, IdDetalleCompra AS idC, CantidadRemitida AS q FROM dbo.tblRemitoCompra")
    contactos = {c["id"]: c["n"] for c in fetch_all("SELECT IdContacto AS id, [Razon Social] AS n FROM dbo.Contactos")}
    return bases, equiv, prod, remitos, facturas, vinc, contactos


def claves_producto(p: dict | None) -> tuple[set[str], set[str]]:
    if not p:
        return set(), set()
    # En semillas el "principio activo" es el cultivo (MAIZ): no distingue híbridos. Se marca con "CULTIVO:" y solo
    # vale contra un renglón genérico ("Kg. Maiz", "Kg. Avena") que no nombra otra variedad (ver `coincide`).
    if (p["TipoProducto"] or "") == "Semilla":
        cultivo = tokens(p["IngredienteActivo"])
        return tokens(p["Producto"]) - cultivo, {"CULTIVO:" + w for w in cultivo}
    return tokens(p["Producto"]), tokens(p["IngredienteActivo"])


def familia(texto) -> str | None:
    """Familia de fertilizante (las marcas se intercambian, regla del vinculador 050): urea o arrancador (más fósforo)."""
    t = norm(texto)
    if "UREA" in t:
        return "UREA"
    if re.search(r"\b(MAP|DAP|ARRANCADOR|MONOAMON\w*|FOSFATO|PROTERRA)\b", t) or re.search(r"\bNP\s*\d", t):
        return "ARRANCADOR"
    m = re.search(r"\b(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})\b", t)
    if m and int(m.group(2)) > int(m.group(1)):
        return "ARRANCADOR"
    return None


SERVICIO = re.compile(r"^(HAS|HECTAREAS|HA|SIEMBRA|RESIEMBRA|FERTILIZACION|FERTILIZADA|DISCO|DIF|VOLEO|EXTRACCION|TRABAJOS|TBJS|FLETE)( |$)")


IA_GENERICAS = {"EQUIVAL", "ACIDO", "SIMPLE", "FOLIAR", "FERTIRR", "USO"}


def _nombre_en_texto(nombre_completo: str, texto: str) -> bool:
    """El nombre comercial del remito, sin espacios/guiones, dentro del texto de la factura sin espacios; o una
    palabra larga del nombre (6+) con una letra de diferencia contra una palabra del texto."""
    import difflib
    pegado = re.sub(r"[^A-Z0-9]", "", nombre_completo)
    t = norm(texto)
    if len(pegado) >= 6 and pegado in re.sub(r"[^A-Z0-9]", "", t):
        return True
    largas = [w for w in nombre_completo.split() if len(w) >= 6 and not w.isdigit() and w not in GENERICOS]
    return any(difflib.SequenceMatcher(None, w, x).ratio() >= 0.88 for w in largas for x in t.split() if len(x) >= 6)


_NOMBRES: dict[int, str] = {}  # IdProducto → nombre comercial normalizado (lo carga `proponer`)


def coincide(rem_prod: int, nombre: set, ia: set, f: dict, fam: str | None = None, nombre_completo: str = "") -> bool:
    nombre_completo = nombre_completo or _NOMBRES.get(rem_prod, "")
    if SERVICIO.match(norm(f["texto"])):
        return False  # renglón de servicio (labor por hectárea), no es mercadería
    tf = tokens(f["texto"])
    if fam:
        return familia(f["texto"]) == fam  # fertilizante: solo por familia
    if nombre & tf:
        return True
    # Nombre partido o pegado ("Eco-Prochem", "Eco Rizo Spray") o con una letra de diferencia ("CURRINCHE")
    if nombre_completo and _nombre_en_texto(nombre_completo, f["texto"]):
        return True
    cultivo = {w[len("CULTIVO:"):] for w in ia if w.startswith("CULTIVO:")}
    if cultivo:
        # semilla: renglón genérico del mismo cultivo sin otra variedad nombrada
        return bool(cultivo & tf) and not (tf - cultivo - {"SEMILLA", "SEMILLAS", "BOLSAS", "BOLSA"})
    ia_util = ia - IA_GENERICAS
    if ia_util and ia_util <= tf:  # todos los principios activos en el texto
        return True
    if f["prod"] is not None and int(f["prod"]) == rem_prod and not tf:
        return True
    if f["prod"] is not None and int(f["prod"]) == rem_prod and (nombre or ia) and (tf & (nombre | ia)):
        return True
    return f["prod"] is not None and int(f["prod"]) == rem_prod and not (tf - GENERICOS)


PESOS_BOLSA = (20.0, 25.0, 40.0, 50.0)


def factores(f: dict, rem_unidad) -> tuple[float, ...]:
    """Factores posibles para pasar la cantidad del renglón de factura a la unidad del remito (la unidad de la
    factura suele faltar): toneladas → kg, bolsas → kg (peso del texto o los usuales), presentación 'X 5 L'."""
    t = norm(f["texto"])
    u = norm(f["unidad"])
    ru = norm(rem_unidad)
    en_kg = ru.startswith("KG") or ru.startswith("KILO")
    out = [1.0]
    # Toneladas: unidad TON, texto "Ton./Toneladas/Toneledas…", o granel de fertilizante sin unidad con cantidad
    # chica (misma regla que el vinculador 050).
    granel_sin_unidad = (familia(t) is not None and not u and not re.match(r"^(KG|KILO)", t)
                         and float(f["cant"]) < 100)
    if en_kg and (u.startswith("TON") or re.match(r"^(TON|TN)\w*", t) or granel_sin_unidad):
        return (1000.0,)
    if en_kg and (u.startswith("BOL") or re.match(r"^BOLSA", t)):
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*(KG|KGS|KILOS)\b", t.replace(" ,", ","))
        out = [float(m.group(1).replace(",", "."))] if m else list(PESOS_BOLSA)
        return tuple(out + [1.0])
    m = re.search(r"X\s*(\d+(?:[.,]\d+)?)\s*(KG|KGS|L|LT|LTS|LITROS)\b", t.replace(" ,", ","))
    if m:
        k = float(m.group(1).replace(",", "."))
        if k > 0:
            out += [k, 1 / k]
    return tuple(out)


# Vínculos verificados uno por uno contra la factura (21/11/2026): la factura usa el nombre genérico o el principio
# activo y la regla automática no los reconoce. IdDetalleRemito → renglones de factura (IdDetalleCompra).
CONFIRMADOS: dict[int, list[int]] = {
    359: [2141374335],  # Pionero (lotus tenuis) 50 kg ↔ Bayá 0020-00314873 19/01/2023 "LOTUS TENUIS PEL/CURADO"
    360: [2141374336],  # Brujo (lotus corniculatus) 50 kg ↔ misma factura "LOTUS CORNICULATUS"
    66: [2141369159, 2141369092, 2141369093, 2141369094, 2141369261, 2141369820, 2141369821],  # Lexplus 10 L ↔ Bayá 0020-00183136 "Lex Plus"
    61: [2141366997, 2141367337, 2141367338, 2141367339, 2141367340, 2141368047, 2141368048, 2141368049, 2141368050,
         2141369806, 2141369808],  # NV Atanor C 300 L ↔ Cargill 1125-00000894 31/10/2017 "2,4D Sal" (300 L)
    112: [2141366349, 2141367323],  # Backup WG 4 kg ↔ Lartirigoyen 0149-00003552 "Clorimuron" 3,9 + 0,1
    302: [2141373390, 2141373576, 2141373577, 2141373578, 2141373579],  # 2,4D Lanther 80 L ↔ Bayá 0020-00289971 "2,4 D 89% ETIL HEXIL" (80 L)
    312: [2141373879, 2141373880, 2141373881, 2141373882, 2141373580, 2141373471, 2141373581, 2141373582, 2141373583,
          2141375318, 2141375319, 2141375320],  # 2,4D Lanther 220 L ↔ Bayá 0020-00292987 (220 L)
    335: [2141374441, 2141374442],  # Inoculante 3 ↔ Bayá 0020-00316796 "INOC SOJA EBC" 2 + 1
    403: [2141375517, 2141375563, 2141375741],  # Inoculante 4 ↔ Bayá 0020-00357848 "PACK INOC SOJA EBC" 2 + 1 + 1
    514: [2141378220],  # Inoculante 4 ↔ Bayá 0020-00451190 "INOC SOJA EBC" 4
    354: [2141373773],  # DM 46R18 4.720 kg ↔ Lartirigoyen 0149-00010918 118 bolsas × 40 kg
    135: [2141365906, 2141367081, 2141367082, 2141367083, 2141367084],  # Rizo Spray Sulfo 105 L ↔ FEDEA 1003-00000335
    23: [2141365892, 2141367295, 2141367296, 2141367297],  # TTM 20 L ↔ FEDEA 1003-00000331 "Coadyuvante TTM"
    253: [2141373532, 2141373533, 2141373534, 2141372036, 2141372316, 2141372317, 2141372318, 2141372636, 2141372637,
          2141372638, 2141373372, 2141373538, 2141373539, 2141373540, 2141372044],  # Dicamba 40 L ↔ Bayá 0020-00250733 (30) + 0020-00250734 (10)
    269: [2141371991],  # Baguette 620 5.080 kg ↔ Lartirigoyen 0149-00009398 "Semilla Trigo B620"
    451: [2141377065, 2141377600],  # DM 40R21 6.000 kg ↔ Bayá 0020-00401517 "SOJA DM 40 R 21" 1.400 + 4.600
    428: [2141378585, 2141376159],  # Avena común 4.000 kg ↔ Lartirigoyen 0149-00012509 1.890 + 2.110 (hoy 4.000 contra el de 2.110)
}


BAYA = 226
ORIGEN_JSON = Path(__file__).resolve().parents[2] / "backups" / "baya-origen-remitos.json"


def clave_remito(nro) -> tuple | None:
    """'0043-00017804', '0043-0003364', ' 0043 00017804' → (43, 17804)."""
    m = re.findall(r"\d+", str(nro or ""))
    return (int(m[0]), int(m[1])) if len(m) >= 2 else None


def _desc(t) -> str:
    t = norm(t)
    t = re.sub(r"^(LTS|LT|KG|KGS|KILOS|LITROS|BOLSAS|UNI|PACK)\s+", "", t)
    return re.sub(r"[^A-Z0-9]", "", t)[:16]


PREFIJOS_REMITO = {"0043", "0050"}  # remitos de Bayá; "0006-…" en el origen es otro comprobante (pedido)


def origen_baya(facturas) -> dict[int, str]:
    """IdDetalleCompra → remito de origen según el PDF de Bayá (scripts/baya_origen_remitos.py). Si un producto
    aparece en varios renglones del PDF con remitos distintos, los renglones del sistema se reparten por cantidad."""
    if not ORIGEN_JSON.exists():
        return {}
    pdf = json.loads(ORIGEN_JSON.read_text(encoding="utf-8"))
    por_compra = defaultdict(list)
    for f in facturas:
        if f["prov"] == BAYA:
            por_compra[str(f["idCompra"])].append(f)
    out = {}
    for idc, fs in por_compra.items():
        rengs = [g for g in ((pdf.get(idc) or {}).get("renglones") or []) if g["remito"][:4] in PREFIJOS_REMITO]
        if not rengs:
            continue
        if len({g["remito"] for g in rengs}) == 1 and len(rengs) == len((pdf.get(idc) or {}).get("renglones") or []):
            for f in fs:  # un solo remito en toda la factura: vale para todos sus renglones
                out[f["idC"]] = rengs[0]["remito"]
            continue
        por_desc = defaultdict(list)
        for g in rengs:
            por_desc[_desc(g["descripcion"])[:12]].append(g)
        for clave, gs in por_desc.items():
            dbs = [f for f in fs if _desc(f["texto"])[:12] == clave and f["idC"] not in out]
            if not dbs:
                continue
            remitos_distintos = {g["remito"] for g in gs}
            if len(remitos_distintos) == 1:
                for f in dbs:
                    out[f["idC"]] = gs[0]["remito"]
                continue
            libres = list(dbs)
            for g in sorted(gs, key=lambda g: -g["cantidad"]):
                for n in range(1, min(len(libres), 8) + 1):
                    combo = next((c for c in combinations(libres, n) if iguales(sum(float(f["cant"]) for f in c), g["cantidad"])), None)
                    if combo:
                        for f in combo:
                            out[f["idC"]] = g["remito"]
                            libres.remove(f)
                        break
    return out


def proponer(remitos, facturas, prod, bases, equiv):
    _NOMBRES.clear()
    _NOMBRES.update({k: norm(v["Producto"]) for k, v in prod.items()})
    fact_prov = defaultdict(list)
    for f in facturas:
        fact_prov[f["prov"]].append(f)
    resto = {f["idC"]: float(f["cant"]) for f in facturas}  # en unidades de la factura
    propuesta: dict[int, dict] = {}
    por_id = {f["idC"]: f for f in facturas}
    cant_remito = {r["idR"]: float(r["cant"]) for r in remitos}
    for idr, ids in CONFIRMADOS.items():
        if idr in cant_remito and all(i in por_id for i in ids):
            k = cant_remito[idr] / sum(resto[i] for i in ids)  # unidad de la factura → del remito (bolsas → kg)
            propuesta[idr] = {"estado": "PROPUESTO", "items": [
                {"idC": i, "q": resto[i] * k, "qf": resto[i], "factor": k} for i in ids]}
            for i in ids:
                resto[i] = 0.0

    # Pasada ORIGEN (Bayá desde 10/2021): la factura dice en cada renglón qué remito factura. Manda el proveedor.
    origen = origen_baya(facturas)
    por_remito_origen = defaultdict(list)
    for f in facturas:
        if f["idC"] in origen:
            por_remito_origen[clave_remito(origen[f["idC"]])].append(f)
    rem_por_nro = defaultdict(list)
    for r in remitos:
        if r["prov"] == BAYA:
            rem_por_nro[clave_remito(r["nro"])].append(r)
    for _segunda, (clave, rems) in [(seg, kv) for seg in (False, True) for kv in rem_por_nro.items()]:
        lineas = [f for f in por_remito_origen.get(clave, [])]
        if not lineas:
            continue
        if _segunda:
            # por cantidad, solo con renglones que no son de otro producto del mismo remito
            otros = [x for x in rems if x["idR"] not in propuesta]
            lineas = [f for f in lineas if not any(coincide(int(x["prod"]), *claves_producto(prod.get(int(x["prod"]))), f)
                                                   for x in rems if x["idR"] in propuesta)]
            if not otros:
                continue
        for r in sorted(rems, key=lambda x: x["idR"]):
            if r["idR"] in propuesta:
                continue
            p = prod.get(int(r["prod"]))
            nombre, ia = claves_producto(p)
            fam = familia(p["Producto"]) if p and (p["TipoProducto"] or "") == "Fertilizante" else None
            libres = [f for f in lineas if resto[f["idC"]] > EPS]
            mias = [f for f in libres if coincide(int(r["prod"]), nombre, ia, f, fam)]
            elegidas = None
            for grupo in ((mias,) if not _segunda else (libres[:20],)):
                # todas las del producto, o la combinación que sume la cantidad del remito
                if grupo and iguales(sum(resto[f["idC"]] * factores(f, r["unidad"])[0] for f in grupo), float(r["cant"])):
                    elegidas = grupo
                    break
                for n in range(1, min(len(grupo), 8) + 1):
                    combo = next((c for c in combinations(grupo, n)
                                  if iguales(sum(resto[f["idC"]] * factores(f, r["unidad"])[0] for f in c), float(r["cant"]))), None)
                    if combo:
                        elegidas = list(combo)
                        break
                if elegidas:
                    break
            if elegidas:
                propuesta[r["idR"]] = {"estado": "ORIGEN", "items": [
                    {"idC": f["idC"], "q": resto[f["idC"]] * factores(f, r["unidad"])[0], "qf": resto[f["idC"]],
                     "factor": factores(f, r["unidad"])[0]} for f in elegidas]}
                for f in elegidas:
                    resto[f["idC"]] = 0.0

    # Pasada 0: una factura cuyos renglones del producto, TODOS juntos, suman exactamente un remito. Se asignan
    # primero, de la pareja más cercana en fecha a la más lejana, para que un remito anterior no le tome a otro
    # parte de su factura.
    parejas = []
    for r in remitos:
        p = prod.get(int(r["prod"]))
        nombre, ia = claves_producto(p)
        fam = familia(p["Producto"]) if p and (p["TipoProducto"] or "") == "Fertilizante" else None
        fr = d(r["fecha"])
        por_c = defaultdict(list)
        for f in fact_prov.get(r["prov"], []):
            if abs((d(f["fecha"]) - fr).days) <= VENTANA and coincide(int(r["prod"]), nombre, ia, f, fam):
                por_c[f["idCompra"]].append(f)
        for idc, fs in por_c.items():
            comunes = set(factores(fs[0], r["unidad"]))
            for f in fs[1:]:
                comunes &= set(factores(f, r["unidad"]))
            k = next((k for k in sorted(comunes, key=lambda k: k != 1.0) if iguales(sum(float(f["cant"]) for f in fs) * k, float(r["cant"]))), None)
            if k is not None:
                parejas.append((abs((d(fs[0]["fecha"]) - fr).days), r["idR"], idc, k, fs))
    parejas.sort(key=lambda x: (x[0], x[1]))
    usados_c = set()
    for dist0, idr, idc, k, fs in parejas:
        if idr in propuesta or idc in usados_c or any(resto[f["idC"]] < float(f["cant"]) - EPS for f in fs):
            continue
        empates = [x for x in parejas if x[1] == idr and x[2] != idc and x[0] == dist0 and x[2] not in usados_c]
        propuesta[idr] = {"estado": "EMPATE" if empates else "PROPUESTO",
                          "items": [{"idC": f["idC"], "q": float(f["cant"]) * k, "qf": float(f["cant"]), "factor": k} for f in fs]}
        usados_c.add(idc)
        for f in fs:
            resto[f["idC"]] = 0.0

    for r in remitos:
        if r["idR"] in propuesta:
            continue
        p = prod.get(int(r["prod"]))
        nombre, ia = claves_producto(p)
        fam = familia(p["Producto"]) if p and (p["TipoProducto"] or "") == "Fertilizante" else None
        q = float(r["cant"])
        fr = d(r["fecha"])
        cand = [f for f in fact_prov.get(r["prov"], []) if abs((d(f["fecha"]) - fr).days) <= VENTANA
                and resto[f["idC"]] > EPS and coincide(int(r["prod"]), nombre, ia, f, fam)]
        if not cand:
            propuesta[r["idR"]] = {"estado": "SIN_CANDIDATO", "items": []}
            continue
        mejor = None
        por_fac = defaultdict(list)
        for f in cand:
            por_fac[f["idCompra"]].append(f)

        def dist(fs):
            return max(abs((d(f["fecha"]) - fr).days) + (0 if d(f["fecha"]) >= fr else 15) for f in fs)

        opciones = []

        def probar(combo, n_orden):
            comunes = set(factores(combo[0], r["unidad"]))
            for f in combo[1:]:
                comunes &= set(factores(f, r["unidad"]))
            for k in sorted(comunes, key=lambda k: k != 1.0):  # primero sin conversión
                if iguales(sum(resto[f["idC"]] * k for f in combo), q):
                    opciones.append((n_orden, dist(combo), k, tuple(combo)))
                    return

        # a) renglones de UNA factura cuya suma es la del remito
        for idc, fs in por_fac.items():
            fs = sorted(fs, key=lambda f: f["idC"])
            if len(fs) > 10:
                probar(fs, len(fs))  # la factura entera (Sergio parte un producto en muchos renglones)
            fs = fs[:10]
            for n in range(1, len(fs) + 1):
                for combo in combinations(fs, n):
                    probar(combo, n)
        # b) varias facturas (hasta 3) con un renglón cada una
        if not opciones and len(cand) <= 25:
            for n in (2, 3):
                for combo in combinations(cand, n):
                    if len({f["idCompra"] for f in combo}) == n:
                        probar(combo, 10 + n)
        if opciones:
            opciones.sort(key=lambda o: (o[1], o[0]))
            mejor = opciones[0]
            empate = [o for o in opciones[1:] if o[1] == mejor[1] and {f["idCompra"] for f in o[3]} != {f["idCompra"] for f in mejor[3]}]
            k, combo = mejor[2], mejor[3]
            items = []
            for f in combo:
                items.append({"idC": f["idC"], "q": resto[f["idC"]] * k, "qf": resto[f["idC"]], "factor": k})
                resto[f["idC"]] = 0.0
            propuesta[r["idR"]] = {"estado": "EMPATE" if empate else "PROPUESTO", "items": items,
                                   "alternativas": [o[3] for o in empate[:3]]}
        else:
            propuesta[r["idR"]] = {"estado": "SIN_EXACTA", "items": [], "candidatos": cand}

    # 2ª pasada: una factura (sus renglones del producto) que cubre VARIOS remitos libres (camiones de granel,
    # entregas parciales). Parte de la factura; hasta 6 remitos dentro de la ventana; la combinación más cercana.
    rem_libres = [r for r in remitos if not propuesta[r["idR"]]["items"]]
    info = {}
    for r in rem_libres:
        p = prod.get(int(r["prod"]))
        nombre, ia = claves_producto(p)
        fam = familia(p["Producto"]) if p and (p["TipoProducto"] or "") == "Fertilizante" else None
        info[r["idR"]] = (nombre, ia, fam)
    por_compra = defaultdict(list)
    for f in facturas:
        if resto[f["idC"]] > EPS:
            por_compra[f["idCompra"]].append(f)
    for idc, fs in sorted(por_compra.items(), key=lambda x: x[1][0]["fecha"]):
        ff = d(fs[0]["fecha"])
        libres = [r for r in rem_libres if not propuesta[r["idR"]]["items"] and r["prov"] == fs[0]["prov"]
                  and abs((d(r["fecha"]) - ff).days) <= VENTANA]
        if len(libres) < 2:
            continue
        # agrupa los renglones de la factura por el remito-producto que los reconoce
        for r0 in libres:
            if propuesta[r0["idR"]]["items"]:
                continue
            nombre, ia, fam = info[r0["idR"]]
            lineas = [f for f in fs if resto[f["idC"]] > EPS and coincide(int(r0["prod"]), nombre, ia, f, fam)]
            if not lineas:
                continue
            hermanos = [r for r in libres if not propuesta[r["idR"]]["items"] and
                        all(coincide(int(r["prod"]), *info[r["idR"]][:2], f, info[r["idR"]][2]) for f in lineas)]
            hermanos.sort(key=lambda r: abs((d(r["fecha"]) - ff).days))
            hermanos = hermanos[:12]
            comunes = set(factores(lineas[0], r0["unidad"]))
            for f in lineas[1:]:
                comunes &= set(factores(f, r0["unidad"]))
            total_f = sum(resto[f["idC"]] for f in lineas)
            elegido = None
            for n in range(2, min(6, len(hermanos)) + 1):
                for combo in combinations(hermanos, n):
                    sq = sum(float(r["cant"]) for r in combo)
                    k = next((k for k in sorted(comunes, key=lambda k: k != 1.0) if iguales(total_f * k, sq)), None)
                    if k is not None:
                        dd = max(abs((d(r["fecha"]) - ff).days) for r in combo)
                        if elegido is None or dd < elegido[0]:
                            elegido = (dd, combo, k)
                if elegido:
                    break
            if not elegido:
                continue
            _, combo, k = elegido
            sq = sum(float(r["cant"]) for r in combo)
            for r in combo:
                parte = float(r["cant"]) / sq
                propuesta[r["idR"]] = {"estado": "PROPUESTO (varios remitos)", "items": [
                    {"idC": f["idC"], "q": resto[f["idC"]] * k * parte, "qf": resto[f["idC"]] * parte, "factor": k} for f in lineas]}
            for f in lineas:
                resto[f["idC"]] = 0.0

    # 3ª pasada «por saldo» (granel y semilla que el proveedor factura por campaña, p. ej. Yanquelen): cuenta por
    # proveedor y producto; cada remito libre toma, en orden, lo que queda de los renglones de factura del producto
    # más cercanos en fecha (hasta 400 días), aunque las cantidades no coincidan una a una. Lo que no se cubre queda
    # a la vista como diferencia.
    for r in remitos:
        if propuesta[r["idR"]]["items"]:
            continue
        p = prod.get(int(r["prod"]))
        if not p or (p["TipoProducto"] or "") not in ("Fertilizante", "Semilla"):
            continue
        nombre, ia = claves_producto(p)
        fam = familia(p["Producto"]) if (p["TipoProducto"] or "") == "Fertilizante" else None
        fr = d(r["fecha"])
        q = float(r["cant"])
        lineas = [f for f in fact_prov.get(r["prov"], []) if resto[f["idC"]] > EPS and abs((d(f["fecha"]) - fr).days) <= 400
                  and coincide(int(r["prod"]), nombre, ia, f, fam)]
        lineas.sort(key=lambda f: (abs((d(f["fecha"]) - fr).days), f["idC"]))
        items, falta = [], q
        for f in lineas:
            if falta <= EPS:
                break
            fs = [k for k in factores(f, r["unidad"]) if k != 1.0] or [1.0]
            if len(fs) > 1:
                # bolsas sin peso en el texto: el renglón entero cubre lo que falta del remito (el kg lo da el remito)
                items.append({"idC": f["idC"], "q": falta, "qf": resto[f["idC"]], "factor": falta / resto[f["idC"]]})
                resto[f["idC"]] = 0.0
                falta = 0.0
                break
            k = fs[0]
            disp = resto[f["idC"]] * k
            toma = min(disp, falta)
            items.append({"idC": f["idC"], "q": toma, "qf": toma / k, "factor": k})
            resto[f["idC"]] -= toma / k
            falta -= toma
        if items:
            propuesta[r["idR"]] = {"estado": "POR SALDO", "items": items, "falta": falta}
    return propuesta


def main():
    bases, equiv, prod, remitos, facturas, vinc, contactos = cargar()
    fac = {f["idC"]: f for f in facturas}
    fac_todas = {f["idC"]: f for f in fetch_all(
        """SELECT dc.IdDetalleCompra AS idC, dc.IdCompra AS idCompra, c.Fecha AS fecha, c.IdContacto AS prov, c.[Nro Documento] AS nro,
                  dc.Cantidad AS cant, dc.[Producto/Servicio] AS texto, NULLIF(dc.IdFormulado,0) AS prod
           FROM dbo.Det_Compras dc JOIN dbo.Compras c ON c.IdDeuda = dc.IdCompra
           WHERE dc.IdDetalleCompra IN (SELECT IdDetalleCompra FROM dbo.tblRemitoCompra)""")}
    actuales = defaultdict(list)
    for v in vinc:
        actuales[v["idR"]].append(v)
    prop = proponer(remitos, facturas, prod, bases, equiv)
    # Cobertura de cada remito según el costeo del sistema (convierte unidades: t → kg, bolsas → kg).
    from src.features.remitos.stock_datos import calcular_stock
    cubierto = {c["idDetalle"]: c.get("estadoCosto") == "completo"
                for st in calcular_stock().values() for c in st["capas"] if c.get("origen") == "remito"}

    filas, cambios_prod = [], {}
    REGLA = {"ORIGEN": "Bayá: la factura dice el remito de origen", "PROPUESTO": "cantidad exacta, mismo proveedor y producto",
             "EMPATE": "cantidad exacta, hay otra factura igual de cercana", "POR SALDO": "granel/semilla: cuenta por producto",
             "PROPUESTO (varios remitos)": "una factura para varios remitos (granel)"}
    for r in remitos:
        p = prod.get(int(r["prod"]))
        a = actuales.get(r["idR"], [])
        pr = prop[r["idR"]]
        if pr["estado"] == "POR SALDO" and a:
            pr = {"estado": "SIN_EXACTA", "items": []}  # por saldo solo para remitos sin ningún vínculo hoy
        set_a = {v["idC"] for v in a}
        set_p = {it["idC"] for it in pr["items"]}
        q_act = sum(float(v["q"] or 0) for v in a)
        if pr["items"]:
            docs_a = {(fac.get(i) or fac_todas.get(i) or {}).get("idCompra") for i in set_a}
            docs_p = {fac[i]["idCompra"] for i in set_p}
            sin_exceso = all(float(v["q"] or 0) <= float((fac.get(v["idC"]) or fac_todas.get(v["idC"]) or {}).get("cant") or 0) * 1.02 + 1e-6
                             for v in a)
            mismo_doc = docs_a == docs_p and cubierto.get(r["idR"], False) and sin_exceso
            estado = "OK" if set_a == set_p or mismo_doc else ("NUEVO" if not set_a else "CAMBIO")
            if pr["estado"] == "ORIGEN":
                estado += " (origen en factura)"
            if pr["estado"] == "POR SALDO":
                estado += " (por saldo)"
            if pr["estado"] == "EMPATE":
                estado += " (empate)"
        else:
            estado = "OK sin regla" if set_a and cubierto.get(r["idR"], False) else ("REVISAR" if set_a else "SIN FACTURA")
        def desc(ids, src):
            out = []
            for i in sorted(ids):
                f = src.get(i) or fac_todas.get(i)
                out.append(f"{f['nro']} {d(f['fecha'])} [{f['texto']}] {float(f['cant']):g}" if f else str(i))
            return " | ".join(out)
        filas.append({
            "Estado": estado, "IdDetalleRemito": r["idR"], "Fecha remito": d(r["fecha"]), "Remito": r["nro"],
            "Proveedor": contactos.get(r["prov"], r["prov"]), "Producto": p["Producto"] if p else r["prod"], "IdProducto": int(r["prod"]),
            "Cantidad": float(r["cant"]), "Unidad": r["unidad"],
            "Vinculado hoy": desc(set_a, fac), "Cant. vinculada hoy": q_act,
            "Propuesto": desc(set_p, fac),
            "Regla": ("verificado a mano contra la factura" if r["idR"] in CONFIRMADOS else REGLA.get(pr["estado"], "")) if pr["items"] else "",
            "Sin cubrir (por saldo)": round(pr.get("falta", 0.0), 3),
            "Candidatos (sin exacta)": desc({f["idC"] for f in pr.get("candidatos", [])}, fac)[:500],
        })
        for it in pr["items"]:
            f = fac[it["idC"]]
            if f["prod"] is None or int(f["prod"]) != int(r["prod"]):
                cambios_prod[it["idC"]] = {"IdDetalleCompra": it["idC"], "Factura": f["nro"], "Fecha": d(f["fecha"]), "Texto": f["texto"],
                                           "IdFormulado hoy": f["prod"], "Producto hoy": (prod.get(int(f["prod"])) or {}).get("Producto") if f["prod"] else None,
                                           "IdFormulado propuesto": int(r["prod"]), "Producto propuesto": p["Producto"] if p else None}

    import openpyxl
    from openpyxl.utils import get_column_letter
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Remitos"
    cols = list(filas[0].keys())
    ws.append(cols)
    orden = {"CAMBIO": 0, "NUEVO": 1, "REVISAR": 2, "SIN FACTURA": 3, "OK sin regla": 4, "OK": 5}
    for f in sorted(filas, key=lambda x: (orden.get(x["Estado"].split(" (")[0], 9), x["Fecha remito"])):
        ws.append([f[c] for c in cols])
    ws2 = wb.create_sheet("Producto en factura")
    if cambios_prod:
        c2 = list(next(iter(cambios_prod.values())).keys())
        ws2.append(c2)
        for v in cambios_prod.values():
            ws2.append([v[c] for c in c2])
    for w in (ws, ws2):
        w.freeze_panes = "A2"
        for i in range(1, w.max_column + 1):
            w.column_dimensions[get_column_letter(i)].width = 18
    ws0 = wb.create_sheet("Resumen", 0)
    ws0.append(["Estado", "Renglones de remito", "Qué significa"])
    expl = {"OK": "el vínculo de hoy es el correcto (no se toca)", "OK sin regla": "vínculo de hoy cubre la cantidad; la regla no lo reproduce (no se toca)",
            "NUEVO": "sin vínculo hoy; se vincula a la factura propuesta", "CAMBIO": "hoy vinculado a otra factura; se reemplaza por la propuesta",
            "REVISAR": "vínculo de hoy no cubre la cantidad y no hay propuesta (no se toca)", "SIN FACTURA": "no se encontró la factura (no se toca)"}
    cnt = defaultdict(int)
    for f in filas:
        cnt[f["Estado"]] += 1
    for k in sorted(cnt, key=lambda k: (orden.get(k.split(" (")[0], 9), k)):
        ws0.append([k, cnt[k], expl.get(k.split(" (")[0], "")])
    ws0.column_dimensions["A"].width = 32
    ws0.column_dimensions["C"].width = 80
    salida = Path(__file__).resolve().parents[2] / "specs" / "050-tamizado-imputacion-cultivos" / f"auditoria-vinculos-remitos-{date.today():%Y%m%d}.xlsx"
    wb.save(salida)
    # Propuesta exacta para aplicar (lo que se aprueba es lo que se escribe): solo NUEVO y CAMBIO.
    aplicar = {"vinculos": [], "productos": list(cambios_prod.values())}
    for r in remitos:
        pr = prop[r["idR"]]
        if pr["estado"] == "POR SALDO" and actuales.get(r["idR"]):
            continue
        fila = next(f for f in filas if f["IdDetalleRemito"] == r["idR"])
        if fila["Estado"].split(" (")[0] in ("NUEVO", "CAMBIO"):
            aplicar["vinculos"].append({"idDetalleRemito": r["idR"], "estado": fila["Estado"], "hoy": [v["idC"] for v in actuales.get(r["idR"], [])],
                                        "items": [{"idDetalleCompra": it["idC"], "cantidadFactura": it["qf"]} for it in pr["items"]]})
    # Un renglón de factura propuesto que hoy está vinculado a un remito que NO se toca se contaría dos veces:
    # esa propuesta sale de la tanda y va a «Conflictos» (los dos remitos quedan como hoy). Se repite hasta estabilizar.
    conflictos = []
    while True:
        tocados = {v["idDetalleRemito"] for v in aplicar["vinculos"]}
        usados_fuera = defaultdict(list)
        for v in vinc:
            if v["idR"] not in tocados:
                usados_fuera[v["idC"]].append(v["idR"])
        malos = [v for v in aplicar["vinculos"] if any(it["idDetalleCompra"] in usados_fuera for it in v["items"])]
        if not malos:
            break
        for v in malos:
            otros = sorted({x for it in v["items"] for x in usados_fuera.get(it["idDetalleCompra"], [])})
            conflictos.append({**v, "remitosQueLoUsanHoy": otros})
            aplicar["vinculos"].remove(v)
    aplicar["conflictos"] = conflictos
    salida.with_suffix(".json").write_text(json.dumps(aplicar, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    wb = openpyxl.load_workbook(salida)
    wc = wb.create_sheet("Conflictos")
    wc.append(["IdDetalleRemito", "Estado propuesto", "Remitos que hoy usan esas facturas", "Remito", "Fecha", "Producto", "Cantidad", "Propuesto"])
    por_r = {f["IdDetalleRemito"]: f for f in filas}
    for c in conflictos:
        f = por_r[c["idDetalleRemito"]]
        wc.append([c["idDetalleRemito"], c["estado"], ", ".join(map(str, c["remitosQueLoUsanHoy"])), f["Remito"], f["Fecha remito"], f["Producto"], f["Cantidad"], f["Propuesto"]])
    wb.save(salida)
    print("a aplicar:", len(aplicar["vinculos"]), "conflictos:", len(conflictos))
    cuenta = defaultdict(int)
    for f in filas:
        cuenta[f["Estado"]] += 1
    print(dict(cuenta), "productos a corregir en factura:", len(cambios_prod))
    print(salida)


if __name__ == "__main__":
    main()
