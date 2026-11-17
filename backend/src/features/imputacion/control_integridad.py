"""Control de integridad de los costos (050, 17/11/2026, tras la revisión de especialistas).

Verifica solo, en segundo plano y una vez por día, las reglas que, si se rompen, hacen que el costo de un cultivo
salga mal sin que nada avise:
  1. Cada renglón aprobado del esquema nuevo reparte exactamente su importe (al TC del comprobante, más el flete
     que le corresponde) — ni más ni menos.
  2. Ningún renglón tiene dos imputaciones vigentes (de stock y directa a la vez).
  3. En el resultado de cada cultivo/campaña, ninguna factura entra por dos caminos (reparto del contratista y
     esquema nuevo; imputación manual vieja y esquema nuevo).
  4. Ninguna imputación apunta a un renglón de factura que ya no existe.
  5. El listado para el Estudio suma, por documento, lo mismo que el sistema.
El resultado se lista por documento, en lenguaje llano. Solo lectura.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from datetime import datetime, timedelta

from src.db.connection import fetch_all

_log = logging.getLogger(__name__)
_VIGENCIA = timedelta(hours=24)
_estado: dict = {"fecha": None, "problemas": [], "controlando": False, "error": None}
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
            WHERE EXISTS (SELECT 1 FROM dbo.ImputacionPropuestas p WHERE p.IdDetalleCompra = d.IdDetalleCompra AND p.Origen = 'Insumo')
              AND EXISTS (SELECT 1 FROM dbo.ImputacionPropuestas p WHERE p.IdDetalleCompra = d.IdDetalleCompra AND p.Origen = 'Directo')
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
    from src.features.resultado_cultivo import costos

    pares = fetch_all(
        """SELECT DISTINCT p.IdCultivo AS c, p.IdCampania AS ca, cu.Cultivo AS cultivo, x.[Campaña] AS campania
           FROM dbo.ImputacionPropuestas p JOIN dbo.Cultivos cu ON cu.IdCultivo = p.IdCultivo
           JOIN dbo.[Campañas] x ON x.[IdCampaña] = p.IdCampania
           WHERE p.Estado = 'Aprobada' AND p.Origen IN ('Insumo', 'Directo', 'Contratista')
             AND p.FechaCalculo >= '2025-05-12' AND p.IdCultivo IS NOT NULL"""
    )
    dobles: dict[tuple, set] = defaultdict(set)
    for p in pares:
        for camino, id_ in dobles_en_resultado(costos.costo_total(p["c"], p["ca"])["lineas"]):
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


def controlar() -> list[dict]:
    problemas: list[dict] = []
    for control in (_control_dos_imputaciones, _control_huerfanas, _control_renglones, _control_resultado, _control_listado):
        try:
            problemas += control()
        except Exception as exc:  # un control que falla se informa, no tapa a los demás
            _log.exception("Control de integridad: %s", control.__name__)
            problemas.append({"tipo": "No se pudo completar un control", "idCompra": None, "documento": "",
                              "detalle": f"{control.__name__}: {exc}"})
    return problemas


def _correr() -> None:
    try:
        problemas = controlar()
        with _lock:
            _estado.update(fecha=datetime.now(), problemas=problemas, error=None)
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
    lanzar()
    with _lock:
        return {"fecha": _estado["fecha"].isoformat() if _estado["fecha"] else None, "controlando": _estado["controlando"],
                "problemas": list(_estado["problemas"]), "error": _estado["error"]}
