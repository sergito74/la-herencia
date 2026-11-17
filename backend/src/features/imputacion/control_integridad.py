"""Control de integridad de los costos (050, 17/11/2026, tras la revisión de especialistas).

Verifica solo, en segundo plano, una vez por día y cada vez que cambia una imputación, las reglas que, si se rompen, hacen que el costo de un cultivo
salga mal sin que nada avise:
  1. Cada renglón aprobado del esquema nuevo reparte exactamente su importe (al TC del comprobante, más el flete
     que le corresponde) — ni más ni menos.
  2. Ningún renglón tiene dos imputaciones vigentes (de stock y directa a la vez; las reemplazadas no cuentan).
  3. En el resultado de cada cultivo/campaña, ninguna factura entra por dos caminos (reparto del contratista y
     esquema nuevo; imputación manual vieja y esquema nuevo).
  4. Ninguna imputación apunta a un renglón de factura que ya no existe.
  5. El listado para el Estudio suma, por documento, lo mismo que el sistema.
El resultado se lista por documento, en lenguaje llano. Solo lectura.
"""

from __future__ import annotations

import logging
import re
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from src.db.connection import fetch_all

_log = logging.getLogger(__name__)
_VIGENCIA = timedelta(hours=24)
_estado: dict = {"fecha": None, "problemas": [], "controlando": False, "error": None, "huella": None}
_lock = threading.Lock()


def _doc(f: dict) -> str:
    fecha = f.get("fecha")
    fecha = fecha.strftime("%d/%m/%Y") if hasattr(fecha, "strftime") else (str(fecha)[:10] if fecha else "")
    return f"{f.get('proveedor') or ''} · {f.get('tipoDocumento') or ''} {f.get('nroDocumento') or ''} del {fecha}".strip()


_DOC_SQL = """c.IdDeuda AS idCompra, c.Fecha AS fecha, co.[Razon Social] AS proveedor, c.[Tipo documento] AS tipoDocumento,
              c.[Nro Documento] AS nroDocumento"""


# ---- reglas puras (testeables) ----

def renglones_que_no_cierran(renglones: list[dict], fracciones: dict[int, float], flete: dict[int, float]) -> list[dict]:
    """`renglones`: {id, importePesos, esNotaCredito, esFlete, ...doc}; `fracciones`: {id: suma de la imputación vigente}.
    Tolerancia: 5 centavos o la precisión de cantidades y TC (2e-5 relativo)."""
    out = []
    for r in renglones:
        if r.get("esFlete") or r["id"] not in fracciones:
            continue
        esperado = abs(float(r["importePesos"] or 0)) + flete.get(r["id"], 0.0)
        imputado = abs(fracciones[r["id"]])
        if abs(esperado - imputado) > max(0.05, 2e-5 * esperado):
            out.append({**r, "esperado": round(esperado, 2), "imputado": round(imputado, 2)})
    return out


def dobles_en_resultado(lineas: list[dict]) -> list[tuple[str, int]]:
    """Facturas que entran por dos caminos en el costo de un cultivo/campaña."""
    contratista = {l["idCompra"] for l in lineas if l.get("concepto") == "Contratista" and l.get("idCompra")}
    nuevo_compra = {l["idCompra"] for l in lineas if l.get("origen") == "Alcance050" and l.get("concepto") == "Compra"}
    viejo = {l["idDetalleCompra"] for l in lineas if l.get("origen") == "Compra" and l.get("idDetalleCompra")}
    nuevo_renglon = {l["idDetalleCompra"] for l in lineas if l.get("origen") == "Alcance050"}
    return ([("contratista", i) for i in contratista & nuevo_compra]
            + [("manual", i) for i in viejo & nuevo_renglon])


# ---- controles contra la base ----

def _control_renglones() -> list[dict]:
    from src.features.remitos import capas_factura
    from src.features.resultado_cultivo.costos import VIGENTE_050

    renglones = fetch_all(
        f"""
        SELECT d.IdDetalleCompra AS id, {_DOC_SQL}, d.[Producto/Servicio] AS producto,
               ISNULL(d.Cantidad, 0) * ISNULL(d.[Precio Unitario], 0) * CASE WHEN c.Moneda = 'Dolares' THEN ISNULL(c.[Tipo de Cambio], 0) ELSE 1 END AS importePesos,
               CASE WHEN tr.ReglaDepende = 'FleteInsumo' AND tz.Destino = 'CultivoStock' THEN 1 ELSE 0 END AS esFlete
        FROM dbo.TamizRenglones tz
        JOIN dbo.Det_Compras d ON d.IdDetalleCompra = tz.IdDetalleCompra
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto
        LEFT JOIN dbo.TamizRubroDestino tr ON tr.IdRubro = d.IdRubro
        WHERE tz.Vigente = 1 AND tz.Estado = 'Aprobada' AND tz.Destino IN ('CultivoStock', 'Cultivo', 'Ganaderia', 'Estructura')
        """
    )
    fracciones = {
        f["id"]: float(f["s"] or 0)
        for f in fetch_all(
            f"""
            SELECT p.IdDetalleCompra AS id, SUM(p.Importe) AS s FROM dbo.ImputacionPropuestas p
            JOIN dbo.TamizRenglones tz ON tz.IdDetalleCompra = p.IdDetalleCompra AND tz.Vigente = 1
            WHERE p.Origen IN ('Insumo', 'Directo') AND {VIGENTE_050}
            GROUP BY p.IdDetalleCompra HAVING MIN(CASE WHEN p.Estado = 'Aprobada' THEN 1 ELSE 0 END) = 1
            """
        )
    }
    return [
        {"tipo": "El reparto no suma el importe del renglón", "idCompra": r["idCompra"], "documento": _doc(r),
         "detalle": f"{r['producto']}: el renglón vale $ {r['esperado']:,.2f} y lo imputado suma $ {r['imputado']:,.2f}"}
        for r in renglones_que_no_cierran(renglones, fracciones, capas_factura.flete_por_renglon())
    ]


def _control_dos_imputaciones() -> list[dict]:
    return [
        {"tipo": "Renglón con dos imputaciones a la vez", "idCompra": f["idCompra"], "documento": _doc(f),
         "detalle": f"{f['producto']}: tiene imputación de stock y directa; se cuenta dos veces"}
        for f in fetch_all(
            f"""
            SELECT {_DOC_SQL}, d.[Producto/Servicio] AS producto
            FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
            LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto
            WHERE EXISTS (SELECT 1 FROM dbo.ImputacionPropuestas p WHERE p.IdDetalleCompra = d.IdDetalleCompra AND p.Origen = 'Insumo' AND p.Estado <> 'Reemplazada')
              AND EXISTS (SELECT 1 FROM dbo.ImputacionPropuestas p WHERE p.IdDetalleCompra = d.IdDetalleCompra AND p.Origen = 'Directo' AND p.Estado <> 'Reemplazada')
            """
        )
    ]


def _control_huerfanas() -> list[dict]:
    n = fetch_all("SELECT COUNT(DISTINCT p.IdDetalleCompra) AS n FROM dbo.ImputacionPropuestas p WHERE p.Origen <> 'Contratista' "
                  "AND NOT EXISTS (SELECT 1 FROM dbo.Det_Compras d WHERE d.IdDetalleCompra = p.IdDetalleCompra)")[0]["n"]
    if not n:
        return []
    return [{"tipo": "Imputación de un renglón que ya no existe", "idCompra": None, "documento": "",
             "detalle": f"{n} renglón(es) de factura borrados siguen con imputación: su costo sigue sumando"}]


def _control_resultado() -> list[dict]:
    dobles: dict[tuple, set] = defaultdict(set)
    for p, lineas in _datos_resultado():
        for camino, id_ in dobles_en_resultado(lineas):
            dobles[(camino, id_)].add(f"{p['cultivo']} {p['campania']}")
    if not dobles:
        return []
    ids_compra = {i for (c, i) in dobles if c == "contratista"}
    ids_renglon = {i for (c, i) in dobles if c == "manual"}
    docs = {}
    if ids_compra:
        for f in fetch_all(f"SELECT {_DOC_SQL} FROM dbo.Compras c LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto "
                           f"WHERE c.IdDeuda IN ({','.join('?' * len(ids_compra))})", tuple(ids_compra)):
            docs[("contratista", f["idCompra"])] = f
    if ids_renglon:
        for f in fetch_all(f"SELECT d.IdDetalleCompra AS idr, {_DOC_SQL} FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra "
                           f"LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto WHERE d.IdDetalleCompra IN ({','.join('?' * len(ids_renglon))})",
                           tuple(ids_renglon)):
            docs[("manual", f["idr"])] = f
    out = []
    for (camino, id_), cultivos in dobles.items():
        f = docs.get((camino, id_), {})
        motivo = ("se suma por el reparto de las órdenes y además por la imputación del renglón" if camino == "contratista"
                  else "se suma por la imputación cargada a mano y además por el esquema nuevo")
        out.append({"tipo": "Factura contada dos veces en el resultado", "idCompra": f.get("idCompra"), "documento": _doc(f),
                    "detalle": f"{motivo} ({', '.join(sorted(cultivos))})"})
    return out


# ---- fotos de campañas cerradas (17/11/2026): ningún resultado cerrado cambia sin que se vea ----

def campania_cerrada(campania: str, hoy) -> bool:
    """Pura: una campaña está cerrada desde septiembre del año en que termina ('2024/2025' → sep/2025; las de un
    año, como la avena o la pastura '2025', se toman igual que la 2025/2026)."""
    if not campania or not campania[:4].isdigit():
        return False
    fin = int(campania[:4]) + 1
    return (hoy.year, hoy.month) >= (fin, 9)


def clave_documento(l: dict) -> str:
    """Pura: a qué documento pertenece una línea de costo."""
    if l.get("idDetalleCompra"):
        return f"D{l['idDetalleCompra']}"
    if l.get("idCompra"):
        return f"C{l['idCompra']}|{l.get('idOrdenTrabajo') or ''}"
    if l.get("idGasto"):
        return f"G{l['idGasto']}"
    if l.get("idOrdenTrabajo"):
        return f"O{l['idOrdenTrabajo']}|{l.get('concepto')}"
    return f"X{l.get('concepto')}|{l.get('origen')}"


def diferencias(antes: dict[str, float], ahora: dict[str, float], tolerancia: float = 0.01) -> dict[str, float]:
    """Pura: documentos cuyo importe cambió (nuevos, quitados o distintos)."""
    return {k: round(ahora.get(k, 0.0) - antes.get(k, 0.0), 2) for k in set(antes) | set(ahora)
            if abs(ahora.get(k, 0.0) - antes.get(k, 0.0)) > tolerancia}


def _nombre_documento(clave: str) -> str:
    try:
        if clave.startswith("D"):
            f = fetch_all(f"SELECT {_DOC_SQL}, d.[Producto/Servicio] AS producto FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra "
                          "LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto WHERE d.IdDetalleCompra = ?", (int(clave[1:]),))
            return f"{_doc(f[0])} ({f[0]['producto']})" if f else clave
        if clave.startswith("C"):
            f = fetch_all(f"SELECT {_DOC_SQL} FROM dbo.Compras c LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto WHERE c.IdDeuda = ?",
                          (int(clave[1:].split("|")[0]),))
            return _doc(f[0]) if f else clave
        if clave.startswith("O"):
            orden, concepto = clave[1:].split("|")
            return f"Orden {orden} ({concepto.lower()})"
        if clave.startswith("G"):
            return f"Gasto de caja {clave[1:]}"
    except Exception:  # noqa: BLE001
        pass
    return clave


def _control_cerradas() -> list[dict]:
    import json
    from datetime import date, timedelta
    from src.db.connection import execute_write

    hoy = date.today()
    ultimas = {(f["c"], f["ca"]): f for f in fetch_all(
        "SELECT f.IdCultivo AS c, f.IdCampania AS ca, f.PorDocumento AS doc FROM dbo.ResultadoCultivo_Fotos f "
        "WHERE f.IdFoto = (SELECT MAX(x.IdFoto) FROM dbo.ResultadoCultivo_Fotos x WHERE x.IdCultivo = f.IdCultivo AND x.IdCampania = f.IdCampania)")}
    for p, lineas in _datos_resultado():
        if not campania_cerrada(p["campania"], hoy):
            continue
        ahora: dict[str, float] = defaultdict(float)
        for l in lineas:
            ahora[clave_documento(l)] += float(l.get("montoPesos") or 0)
        ahora = {k: round(v, 2) for k, v in ahora.items() if abs(v) > 0.005}
        previa = ultimas.get((p["c"], p["ca"]))
        cambios = diferencias(json.loads(previa["doc"]), ahora) if previa else {}
        if previa is None or cambios:
            execute_write(
                "INSERT INTO dbo.ResultadoCultivo_Fotos (IdCultivo, IdCampania, CostoPesos, CostoDolares, PorDocumento, Cambios) VALUES (?, ?, ?, ?, ?, ?)",
                (p["c"], p["ca"], round(_pesos(lineas), 2), round(_usd(lineas), 2), json.dumps(ahora),
                 json.dumps(cambios) if previa else None))
    desde = hoy - timedelta(days=30)
    out = []
    for f in fetch_all(
        "SELECT f.Fecha, f.Cambios, cu.Cultivo AS cultivo, k.[Campaña] AS campania FROM dbo.ResultadoCultivo_Fotos f "
        "JOIN dbo.Cultivos cu ON cu.IdCultivo = f.IdCultivo JOIN dbo.[Campañas] k ON k.[IdCampaña] = f.IdCampania "
        "WHERE f.Cambios IS NOT NULL AND f.Fecha >= ? ORDER BY f.Fecha DESC", (desde,)):
        cambios = json.loads(f["Cambios"])
        total = sum(cambios.values())
        principales = sorted(cambios.items(), key=lambda kv: -abs(kv[1]))[:5]
        out.append({"tipo": "Cambió el costo de una campaña cerrada", "idCompra": None,
                    "documento": f"{f['cultivo']} {f['campania']} ({str(f['Fecha'])[8:10]}/{str(f['Fecha'])[5:7]}/{str(f['Fecha'])[:4]})",
                    "detalle": f"{'+' if total >= 0 else ''}$ {total:,.2f}: " + "; ".join(
                        f"{_nombre_documento(k)} {'+' if v >= 0 else ''}$ {v:,.2f}" for k, v in principales)})
    return out



# ---- datos compartidos por los controles del resultado (se calculan una vez por corrida) ----

_cache_datos: dict = {}
_DESDE_CAMPANIA = "2022"  # campañas que se controlan (las de un año desde 2022, las dobles desde 2022/2023)


def _pares_con_costo() -> list[dict]:
    return fetch_all(
        f"""
        SELECT DISTINCT x.c, x.ca, cu.Cultivo AS cultivo, k.[Campaña] AS campania FROM (
            SELECT p.IdCultivo AS c, p.IdCampania AS ca FROM dbo.ImputacionPropuestas p
              WHERE p.Estado = 'Aprobada' AND p.IdCultivo IS NOT NULL
            UNION SELECT m.IdCultivo, b.IdCampaña FROM dbo.vw_ResultadosCultivo_CostosBase b
              JOIN dbo.Map_CultivoResultado m ON m.IdDestino = b.IdDestino
            UNION SELECT d.IdCultivo, d.IdCampania FROM dbo.Ordenes_Trabajo_Distrib d WHERE d.Aplicar = 1
            UNION SELECT p.IdCultivo, p.[IdCampaña] FROM dbo.PlanAgricola p
        ) x JOIN dbo.Cultivos cu ON cu.IdCultivo = x.c JOIN dbo.[Campañas] k ON k.[IdCampaña] = x.ca
        WHERE k.[Campaña] LIKE '[12][0-9][0-9][0-9]%' AND LEFT(k.[Campaña], 4) >= '{_DESDE_CAMPANIA}'
        """
    )


def _datos_resultado() -> list[tuple[dict, list[dict]]]:
    if "resultado" not in _cache_datos:
        from src.features.resultado_cultivo import costos

        pares = _pares_con_costo()
        # Cada cultivo/campaña es independiente: se calculan en paralelo (cada consulta abre su propia conexión).
        with ThreadPoolExecutor(max_workers=8) as ex:
            lineas = list(ex.map(lambda p: costos.costo_total(p["c"], p["ca"])["lineas"], pares))
        _cache_datos["resultado"] = list(zip(pares, lineas))
    return _cache_datos["resultado"]


def _plan() -> dict[tuple, float]:
    """(cultivo, campaña) del plan agrícola → hectáreas sembradas (sin los lotes no sembrados)."""
    out: dict[tuple, float] = {}
    for f in fetch_all(
        "SELECT p.IdCultivo AS c, p.[IdCampaña] AS ca, SUM(CASE WHEN ISNULL(p.NoSembrado, 0) = 0 THEN l.Superficie ELSE 0 END) AS ha "
        "FROM dbo.PlanAgricola p JOIN dbo.Lotes l ON l.IdLote = p.IdLote GROUP BY p.IdCultivo, p.[IdCampaña]"
    ):
        out[(f["c"], f["ca"])] = float(f["ha"] or 0)
    return out


def _pesos(lineas) -> float:
    return sum(float(l.get("montoPesos") or 0) for l in lineas)


def _usd(lineas) -> float:
    return sum(float(l.get("montoDolares") or 0) for l in lineas)


# ---- controles de razonabilidad (17/11/2026, auditoría de costos) ----

def campania_anterior(campania: str) -> str | None:
    """Pura: '2025/2026' → '2024/2025'; '2026' → '2025'."""
    if not campania or not campania[:4].isdigit():
        return None
    a = int(campania[:4]) - 1
    return f"{a}/{a + 1}" if len(campania) > 4 else str(a)


def fuera_de_rango(actual: float, anterior: float, minimo: float = 50.0) -> bool:
    """Pura: costo por hectárea más del doble o menos de la mitad que la campaña anterior (ambos por encima de un
    mínimo, para no alarmar por cultivos casi sin costo)."""
    if actual < minimo or anterior < minimo:
        return False
    return actual > 2 * anterior or actual < 0.5 * anterior


def siembra_terminada(campania: str, hoy) -> bool:
    """Pura: ya pasó la siembra: campaña doble desde febrero del año en que termina; de un año, desde julio."""
    if not campania or not campania[:4].isdigit():
        return False
    anio = int(campania[:4])
    return (hoy.year, hoy.month) >= ((anio + 1, 2) if len(campania) > 4 else (anio, 7))


def _control_fuera_del_plan() -> list[dict]:
    """Costo imputado a un cultivo y campaña que no está en el plan agrícola (ej. Soja 1ª en un año sin soja 1ª)."""
    plan = _plan()
    out = []
    for p, lineas in _datos_resultado():
        total = _pesos(lineas)
        if (p["c"], p["ca"]) not in plan and abs(total) > 1000:
            docs = sorted({l.get("idCompra") for l in lineas if l.get("idCompra")})
            out.append({"tipo": "Costo en un cultivo que no está en el plan agrícola", "idCompra": docs[0] if len(docs) == 1 else None,
                        "documento": f"{p['cultivo']} {p['campania']}",
                        "detalle": f"$ {total:,.2f} en {len(docs)} comprobante(s): revisar si el cultivo o la campaña son otros"})
    return out


def _control_dolares() -> list[dict]:
    """Línea de costo con pesos y sin dólares (salvo los ajustes de tipo de cambio, que no suman US$)."""
    ajustes = {f["c"] for f in fetch_all("SELECT IdDeuda AS c FROM dbo.Compras WHERE ISNULL([Ajusta Tipo Cambio], 0) = 1")}
    out = []
    for p, lineas in _datos_resultado():
        sin = [l for l in lineas if abs(float(l.get("montoPesos") or 0)) > 1000 and not l.get("montoDolares")
               and l.get("idCompra") not in ajustes]
        if sin:
            out.append({"tipo": "Costo sin dólares", "idCompra": None, "documento": f"{p['cultivo']} {p['campania']}",
                        "detalle": f"{len(sin)} línea(s) por $ {_pesos(sin):,.2f} no suman US$: el costo en dólares queda bajo"})
    return out


def _control_ingresos_en_costo() -> list[dict]:
    """Cobros, ventas, recuperos o indemnizaciones dentro del costo."""
    import re
    patron = re.compile(r"COBR|VENTA|RECUPER|INDEMN|SINIESTR", re.I)
    out = []
    for p, lineas in _datos_resultado():
        malas = [l for l in lineas if l.get("origen") == "Seguro" or patron.search(f"{l.get('concepto') or ''} {l.get('rubro') or ''}")]
        if malas:
            out.append({"tipo": "Un ingreso está sumado como costo", "idCompra": None, "documento": f"{p['cultivo']} {p['campania']}",
                        "detalle": f"$ {_pesos(malas):,.2f} ({', '.join(sorted({str(l.get('concepto')) for l in malas}))})"})
    return out


def _control_rubros_faltantes() -> list[dict]:
    """Cultivo sembrado sin semilla, sin labores o (si se cosechó) sin cosecha."""
    from src.features.resultado_cultivo import por_parte

    partes, por_rubro = por_parte._partes(), por_parte._parte_por_rubro()
    plan = _plan()
    con_semilla_orden = {(f["c"], f["ca"]) for f in fetch_all(
        "SELECT DISTINCT d.IdCultivo AS c, d.IdCampania AS ca FROM dbo.Ordenes_Trabajo_Distrib d "
        "JOIN dbo.Ordenes_Trabajo_Insumos oi ON oi.IdOrdenInsumo = d.IdOrdenInsumo JOIN dbo.Ordenes_Trabajo ot ON ot.IdOrdenTrabajo = oi.IdOrdenTrabajo "
        "JOIN dbo.vw_ProductosBase pb ON pb.IdProducto = oi.IdProducto WHERE ot.Estado <> 'Anulada' AND d.Aplicar = 1 AND pb.TipoProducto = 'Semilla'")}
    cosechados = {(f["c"], f["ca"]) for f in fetch_all(
        "SELECT IdCultivo AS c, IdCampaña AS ca FROM dbo.ResultadoCultivo_Cierre WHERE ISNULL(SuperficieCosechada, 0) > 0")}
    cosechados |= {(f["c"], f["ca"]) for f in fetch_all(
        "SELECT DISTINCT m.IdCultivo AS c, k.[IdCampaña] AS ca FROM dbo.[Venta Granos] v JOIN dbo.Map_CultivoResultado m ON m.IdGrano = v.IdProducto "
        "JOIN dbo.[Campañas] k ON k.[Campaña] = v.[Campaña]")}
    from datetime import date
    hoy = date.today()
    out = []
    for p, lineas in _datos_resultado():
        if plan.get((p["c"], p["ca"]), 0) <= 0 or not siembra_terminada(p["campania"], hoy):
            continue  # no sembrado, fuera del plan (lo ve otro control) o todavía en siembra
        nombres = {por_parte.parte_de_linea(l, partes, por_rubro) for l in lineas}
        rubros = " ".join(str(l.get("rubro") or "") for l in lineas).upper()
        faltan = []
        if "Semilla" not in nombres and (p["c"], p["ca"]) not in con_semilla_orden:
            faltan.append("semilla")
        if "Labores" not in nombres:
            faltan.append("labores (siembra/pulverización)")
        if (p["c"], p["ca"]) in cosechados and "Cosecha" not in nombres and "COSECHA" not in rubros:
            faltan.append("cosecha")
        if faltan:
            out.append({"tipo": "Le falta un rubro esencial al cultivo", "idCompra": None, "documento": f"{p['cultivo']} {p['campania']}",
                        "detalle": "sin " + ", ".join(faltan) + ": puede faltar una factura o estar imputada a otro cultivo/campaña"})
    return out


def _control_costo_por_hectarea() -> list[dict]:
    """Costo en US$/ha más del doble o menos de la mitad que el mismo cultivo en la campaña anterior (campañas cerradas)."""
    from datetime import date
    plan = _plan()
    por_nombre = {(p["cultivo"], p["campania"]): (p, lineas) for p, lineas in _datos_resultado()}
    out = []
    for (cultivo, campania), (p, lineas) in por_nombre.items():
        ha = plan.get((p["c"], p["ca"]), 0)
        ant = por_nombre.get((cultivo, campania_anterior(campania)))
        if ha <= 0 or ant is None or not campania_cerrada(campania, date.today()):
            continue
        ha_ant = plan.get((ant[0]["c"], ant[0]["ca"]), 0)
        if ha_ant <= 0:
            continue
        actual, anterior = _usd(lineas) / ha, _usd(ant[1]) / ha_ant
        if fuera_de_rango(actual, anterior):
            out.append({"tipo": "Costo por hectárea fuera de lo normal", "idCompra": None, "documento": f"{cultivo} {campania}",
                        "detalle": f"US$ {actual:,.0f}/ha contra US$ {anterior:,.0f}/ha en {campania_anterior(campania)}: revisar"})
    return out


def _control_verificacion_externa() -> list[dict]:
    """Lo que encontró la última verificación externa (portal de Bayá Casal y ARCA); si tiene más de 8 días, se avisa."""
    from src.features.imputacion import verificacion_externa as V

    u = V.ultima()
    if u is None:
        return [{"tipo": "Falta la verificación externa", "idCompra": None, "documento": "",
                 "detalle": "todavía no se cruzó el sistema contra ARCA y el portal de Bayá Casal"}]
    out = [{**x, "idCompra": x.get("idCompra")} for x in u.get("problemas", [])]
    out += [{"tipo": "La verificación externa no pudo completarse", "idCompra": None, "documento": "", "detalle": e}
            for e in u.get("errores", [])]
    if datetime.now() - datetime.fromisoformat(u["fecha"]) > timedelta(days=8):
        out.append({"tipo": "La verificación externa está atrasada", "idCompra": None, "documento": "",
                    "detalle": f"la última fue el {u['fecha'][:10]}"})
    return out


def _control_provisorios() -> list[dict]:
    """Compra provisoria ("PENDIENTE …") cuyo remito ya tiene la factura real o que el proveedor ya facturó: hay que
    darla de baja (si no, la deuda se cuenta dos veces en la cuenta corriente)."""
    out = []
    for c in fetch_all(
        f"SELECT {_DOC_SQL}, c.[Nro Documento] AS nro, c.IdContacto AS idContacto FROM dbo.Compras c LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto "
        "WHERE c.[Nro Documento] LIKE 'PENDIENTE %' AND c.[Tipo documento] = 'Factura'"):
        num = re.sub(r"\D", "", c["nro"] or "")
        if not num:
            continue
        rem = fetch_all(
            "SELECT rd.IdDetalleRemito AS id, "
            "(SELECT COUNT(*) FROM dbo.tblRemitoCompra t JOIN dbo.Det_Compras d ON d.IdDetalleCompra = t.IdDetalleCompra "
            "  JOIN dbo.Compras cc ON cc.IdDeuda = d.IdCompra WHERE t.IdDetalleRemito = rd.IdDetalleRemito AND cc.[Nro Documento] NOT LIKE 'PENDIENTE%') AS facturado, "
            "(SELECT COUNT(*) FROM dbo.RemitoValorProveedor v WHERE v.IdDetalleRemito = rd.IdDetalleRemito) AS pendiente "
            "FROM dbo.Remitos r JOIN dbo.Remitos_Detalles rd ON rd.IdRemito = r.IdRemito WHERE r.IdProveedor = ? AND r.NroRemito LIKE ?",
            (c["idContacto"], f"%{int(num):08d}"))
        if rem and (any(x["facturado"] for x in rem) or not any(x["pendiente"] for x in rem)):
            out.append({"tipo": "Dar de baja una compra provisoria", "idCompra": c["idCompra"], "documento": _doc(c),
                        "detalle": "el remito ya tiene su factura (o el proveedor ya no lo muestra pendiente): la deuda se cuenta dos veces"})
    return out


def _control_unidades() -> list[dict]:
    """Entrada de stock (remito o factura sin remito) desde mayo de 2025 en una unidad sin equivalencia con la unidad
    base del producto: se toma 1 y la cantidad o el costo unitario salen mal (ej. 1,5 TONELADA contada como 1,5 kg)."""
    from src.features.remitos import capas_factura
    from src.features.remitos.stock_datos import equivalencias, factor_a_base, unidades_base
    from src.features.imputacion.tamiz_repository import nombre_producto

    bases, equiv = unidades_base(), equivalencias()
    entradas = [(r["idProducto"], r["unidad"], f"factura {r['nroDocumento']}") for r in capas_factura.renglones_sin_remito()]
    entradas += [(f["p"], f["u"], f"remito {f['n']}") for f in fetch_all(
        "SELECT rd.IdFormulado AS p, rd.[Unidad Medida] AS u, r.NroRemito AS n FROM dbo.Remitos_Detalles rd "
        "JOIN dbo.Remitos r ON r.IdRemito = rd.IdRemito LEFT JOIN dbo.Remitos_Extra e ON e.IdRemito = r.IdRemito "
        "WHERE ISNULL(e.Anulado, 0) = 0 AND r.Fecha >= '2025-05-12' AND rd.IdFormulado IS NOT NULL")]
    entradas += [(f["p"], f["u"], f"orden {f['ot']}") for f in fetch_all(
        "SELECT oi.IdProducto AS p, oi.Unidad AS u, oi.IdOrdenTrabajo AS ot FROM dbo.Ordenes_Trabajo_Insumos oi "
        "JOIN dbo.Ordenes_Trabajo ot ON ot.IdOrdenTrabajo = oi.IdOrdenTrabajo "
        "WHERE ot.Estado <> 'Anulada' AND ISNULL(ot.FechaEjecucion, ot.FechaPedido) >= '2025-05-12'")]
    out = []
    for pid, unidad, doc in entradas:
        if doc.startswith("orden") and (unidad or "").strip().upper() not in ("", (bases.get(pid) or "").upper()):
            out.append({"tipo": "Orden en otra unidad que el stock", "idCompra": None, "documento": doc,
                        "detalle": f"{nombre_producto(pid)}: la orden está en {unidad} y el stock en {bases.get(pid)}; el consumo no se convierte"})
            continue
        if factor_a_base(pid, unidad, bases, equiv)[1]:
            out.append({"tipo": "Unidad sin equivalencia en el stock", "idCompra": None, "documento": doc,
                        "detalle": f"{nombre_producto(pid)}: viene en {unidad} y el stock se lleva en {bases.get(pid)}; se toma 1 a 1"})
    return out


def _control_fletes() -> list[dict]:
    """Flete de insumos sin insumo aprobado al que sumarse: su importe no entra a ningún costo."""
    from src.features.remitos import capas_factura

    out = []
    for fl in capas_factura.fletes_sin_destino():
        f = fetch_all(f"SELECT {_DOC_SQL} FROM dbo.Compras c LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto WHERE c.IdDeuda = ?",
                      (fl["idCompra"],))
        out.append({"tipo": "Flete de insumos que no llega a ningún costo", "idCompra": fl["idCompra"], "documento": _doc(f[0]) if f else "",
                    "detalle": f"$ {fl['pesos']:,.2f}: la factura (y sus relacionadas) no tiene insumos aprobados para sumarle el flete"})
    return out


def dosis_excesiva(dosis: float, habitual: float, veces: float = 5.0) -> bool:
    """Pura: dosis por hectárea de más de `veces` la habitual del producto (un error de tipeo en la cantidad de una
    orden pasa entero al costo del cultivo)."""
    return habitual > 0 and dosis > veces * habitual


def _control_dosis() -> list[dict]:
    """Insumo de una orden (desde mayo de 2025) aplicado en un lote a más de 5 veces la dosis habitual del producto
    (mediana de todas sus aplicaciones, con al menos 6 de referencia)."""
    from statistics import median
    from src.features.imputacion.tamiz_repository import nombre_producto

    filas = fetch_all(
        "SELECT oi.IdOrdenTrabajo AS ot, oi.IdProducto AS p, oi.Unidad AS u, d.CantidadAsignada AS q, d.Superficie AS ha, "
        "ISNULL(ot.FechaEjecucion, ot.FechaPedido) AS f, l.[Numero Lote] AS lote FROM dbo.Ordenes_Trabajo_Distrib d "
        "JOIN dbo.Ordenes_Trabajo_Insumos oi ON oi.IdOrdenInsumo = d.IdOrdenInsumo JOIN dbo.Ordenes_Trabajo ot ON ot.IdOrdenTrabajo = oi.IdOrdenTrabajo "
        "LEFT JOIN dbo.Lotes l ON l.IdLote = d.IdLote "
        "WHERE ot.Estado <> 'Anulada' AND d.Aplicar = 1 AND d.Superficie > 0 AND d.CantidadAsignada > 0")
    hist: dict[int, list[float]] = defaultdict(list)
    for f in filas:
        f["dosis"] = float(f["q"]) / float(f["ha"])
        hist[f["p"]].append(f["dosis"])
    vistos, out = set(), []
    for f in filas:
        if str(f["f"]) < "2025-05-12" or len(hist[f["p"]]) < 6 or (f["ot"], f["p"]) in vistos:
            continue
        habitual = median(hist[f["p"]])
        if dosis_excesiva(f["dosis"], habitual):
            vistos.add((f["ot"], f["p"]))
            out.append({"tipo": "Dosis fuera de lo normal en una orden", "idCompra": None, "documento": f"Orden {f['ot']} (lote {f['lote']})",
                        "detalle": f"{nombre_producto(f['p'])}: {f['dosis']:,.3f} {f['u'] or ''}/ha contra {habitual:,.3f} habitual: revisar la cantidad"})
    return out


def _remito_sin_costo_en_factura(nro_remito: str, producto: str) -> bool:
    """El costo de ese insumo no está en ningún cultivo: la factura del remito no aparece o dejó el producto en
    "Stock" (si la factura lo imputó a mano a un cultivo, el costo ya está ahí)."""
    r = fetch_all("SELECT TOP 1 NroFactura AS nf, COALESCE(IdContacto, IdProveedor) AS prov FROM dbo.Remitos WHERE NroRemito = ?", (nro_remito,))
    if not r or not r[0]["nf"]:
        return True
    clave = re.sub(r"[^A-Z]", "", (producto or "").upper())[:5]
    lineas = []
    for nf in [x.strip() for x in re.split(r"[/,;]", r[0]["nf"]) if x.strip()]:
        lineas += fetch_all(
            "SELECT d.[Producto/Servicio] AS t, de.Destino AS destino FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra "
            "LEFT JOIN dbo.DestinoCompras de ON de.IdDestino = d.IdDestino "
            "WHERE c.IdContacto = ? AND REPLACE(c.[Nro Documento], ' ', '') = REPLACE(?, ' ', '')", (r[0]["prov"], nf))
    mias = [l for l in lineas if clave and clave in re.sub(r"[^A-Z]", "", (l["t"] or "").upper())]
    return not mias or any((l["destino"] or "") == "Stock" for l in mias)


def _control_consumos_sin_costo() -> list[dict]:
    """Orden de una campaña abierta que consumió un remito sin factura vinculada (ni precio del proveedor): ese
    insumo vale $0 en el cultivo. Si la factura existe, hay que vincular el remito (ej. metolaclor de 2023 en "Stock").
    La semilla propia ("SIN REMITO") no se avisa."""
    from datetime import date
    from src.features.resultado_cultivo import costos

    out, vistos = [], set()
    for p, _ in _datos_resultado():
        if campania_cerrada(p["campania"], date.today()):
            continue
        for x in costos.consumos_sin_factura(p["c"], p["ca"]):
            clave = (x["remito"], x["producto"])
            if (x.get("precioProveedor") or x["remito"] in ("SIN REMITO", "sin remito") or clave in vistos
                    or x["cantidad"] < 0.01 or not _remito_sin_costo_en_factura(x["remito"], x["producto"])):
                continue
            vistos.add(clave)
            out.append({"tipo": "Insumo consumido a $ 0 (remito sin factura vinculada)", "idCompra": None,
                        "documento": f"remito {x['remito']}",
                        "detalle": f"{x['producto']}: {x['cantidad']:,.2f} en {p['cultivo']} {p['campania']} (orden {', '.join(map(str, x['ordenes']))}): vincular el remito a su factura"})
    return out


def _control_listado() -> list[dict]:
    from src.features.imputacion import listado_estudio as L

    filas = L.armar_filas()
    sistema = defaultdict(float)
    for r in L._renglones():
        f = r["fecha"].date() if hasattr(r["fecha"], "date") else r["fecha"]
        sistema[(f, r["nroDocumento"], r["razonSocial"])] += float(r["total"] or 0)
    listado = defaultdict(float)
    for f in filas:
        listado[(f[0], f[3], f[1])] += float(f[13] or 0)
    return [
        {"tipo": "El listado para el Estudio no suma igual que el sistema", "idCompra": None,
         "documento": f"{k[2] or ''} · {k[1] or ''} del {k[0].strftime('%d/%m/%Y') if hasattr(k[0], 'strftime') else k[0]}",
         "detalle": f"sistema $ {sistema[k]:,.2f}, listado $ {listado.get(k, 0):,.2f}"}
        for k in sistema if abs(sistema[k] - listado.get(k, 0.0)) > 0.005
    ]


_errores_recalculo: list[dict] = []


def registrar_error_recalculo(descripcion: str, exc: Exception) -> None:
    """17/11/2026: un recálculo de imputación que falla ya no queda solo en el log: se muestra en el control."""
    with _lock:
        _errores_recalculo.append({"fecha": datetime.now(), "detalle": f"{descripcion}: {exc}"})
        del _errores_recalculo[:-50]
    lanzar(forzar=True)  # se vuelve a controlar enseguida


def _control_recalculos() -> list[dict]:
    with _lock:
        errores = list(_errores_recalculo)
    return [{"tipo": "Un recálculo de imputación falló", "idCompra": None, "documento": "",
             "detalle": f"{e['fecha'].strftime('%d/%m/%Y %H:%M')} — {e['detalle']}. Puede haber quedado una imputación vieja."}
            for e in errores]


def _control_distribucion() -> list[dict]:
    """Renglón de orden ejecutada cuya distribución por lote no suma lo usado: parte del costo no llega a ningún cultivo
    (o llega de más)."""
    return [
        {"tipo": "La distribución de una orden no suma lo usado", "idCompra": None, "documento": f"Orden {f['ot']}",
         "detalle": f"{f['producto']}: usado {f['total']:,.2f}, distribuido a los lotes {f['asignado']:,.2f}"}
        for f in fetch_all(
            """
            SELECT oi.IdOrdenTrabajo AS ot, p.Producto AS producto, MAX(oi.CantidadTotal) AS total,
                   SUM(CASE WHEN d.Aplicar = 1 THEN d.CantidadAsignada ELSE 0 END) AS asignado
            FROM dbo.Ordenes_Trabajo_Insumos oi JOIN dbo.Ordenes_Trabajo ot ON ot.IdOrdenTrabajo = oi.IdOrdenTrabajo
            JOIN dbo.Ordenes_Trabajo_Distrib d ON d.IdOrdenInsumo = oi.IdOrdenInsumo
            LEFT JOIN dbo.vw_ProductosBase p ON p.IdProducto = oi.IdProducto
            WHERE ot.Estado <> 'Anulada' AND ot.FechaEjecucion >= '2025-05-12'
            GROUP BY oi.IdOrdenInsumo, oi.IdOrdenTrabajo, p.Producto
            HAVING ABS(MAX(oi.CantidadTotal) - SUM(CASE WHEN d.Aplicar = 1 THEN d.CantidadAsignada ELSE 0 END))
                   > 0.01 * ABS(MAX(oi.CantidadTotal)) + 0.01
            """
        )
    ]


def controlar() -> list[dict]:
    problemas: list[dict] = []
    _cache_datos.clear()
    for control in (_control_recalculos, _control_dos_imputaciones, _control_huerfanas, _control_renglones,
                    _control_distribucion, _control_resultado, _control_fuera_del_plan, _control_dolares,
                    _control_ingresos_en_costo, _control_rubros_faltantes, _control_costo_por_hectarea,
                    _control_cerradas, _control_provisorios, _control_unidades, _control_fletes, _control_dosis, _control_consumos_sin_costo, _control_verificacion_externa, _control_listado):
        try:
            problemas += control()
        except Exception as exc:  # un control que falla se informa, no tapa a los demás
            _log.exception("Control de integridad: %s", control.__name__)
            problemas.append({"tipo": "No se pudo completar un control", "idCompra": None, "documento": "",
                              "detalle": f"{control.__name__}: {exc}"})
    return problemas


def huella() -> tuple:
    """Barata: cambia cuando se guarda, aprueba o reemplaza una imputación o se reclasifica un renglón."""
    f = fetch_all(
        "SELECT (SELECT COUNT(*) FROM dbo.ImputacionPropuestas) AS n, (SELECT MAX(IdPropuesta) FROM dbo.ImputacionPropuestas) AS mx, "
        "(SELECT MAX(FechaAprobacion) FROM dbo.ImputacionPropuestas) AS ap, "
        "(SELECT COUNT(*) FROM dbo.ImputacionPropuestas WHERE Estado = 'Reemplazada') AS rz, "
        "(SELECT COUNT(*) FROM dbo.TamizRenglones) AS nt, (SELECT MAX(FechaCalculo) FROM dbo.TamizRenglones) AS ft, "
        "(SELECT COUNT(*) FROM dbo.Det_Compras) AS nd, (SELECT MAX(IdDetalleCompra) FROM dbo.Det_Compras) AS md"
    )[0]
    return tuple(str(v) for v in f.values())


def _correr() -> None:
    try:
        antes = huella()
        problemas = controlar()
        with _lock:
            _estado.update(fecha=datetime.now(), problemas=problemas, error=None, huella=antes)
    except Exception as exc:
        _log.exception("Control de integridad")
        with _lock:
            _estado.update(error=str(exc))
    finally:
        with _lock:
            _estado["controlando"] = False


def lanzar(forzar: bool = False) -> None:
    """Corre el control en segundo plano si no hay uno en curso y el último tiene más de un día (o `forzar`)."""
    with _lock:
        if _estado["controlando"]:
            return
        vencido = _estado["fecha"] is None or datetime.now() - _estado["fecha"] > _VIGENCIA
        if not (forzar or vencido):
            return
        _estado["controlando"] = True
    threading.Thread(target=_correr, name="control-integridad-costos", daemon=True).start()


def estado() -> dict:
    # Se vuelve a controlar solo si algo cambió desde el último control (una aprobación, una corrección, una factura).
    try:
        cambio = _estado["huella"] is not None and huella() != _estado["huella"]
    except Exception:  # la huella es solo un atajo; si falla, rige la vigencia diaria
        cambio = False
    lanzar(forzar=cambio)
    with _lock:
        return {"fecha": _estado["fecha"].isoformat() if _estado["fecha"] else None, "controlando": _estado["controlando"],
                "problemas": list(_estado["problemas"]), "error": _estado["error"]}
