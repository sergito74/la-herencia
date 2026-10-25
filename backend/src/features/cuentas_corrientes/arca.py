"""Subcuentas analíticas de ARCA: reparto conservativo, sin otro libro contable."""
from datetime import date
from decimal import Decimal
import json
import unicodedata

from src.db.connection import atomic_reconciliation, execute_insert_returning_id
from src.features.cajas_efectivo.operaciones import read

CATALOGO = {
    "iva": "IVA — retenciones, pagos y devoluciones",
    "ganancias": "Ganancias y anticipos",
    "sicore-ganancias": "Retenciones de Ganancias efectuadas — SICORE",
    "autonomos-lucy": "Autónomos Lucy",
    "autonomos-sergio": "Autónomos Sergio",
    "autonomos-pendientes": "Autónomos — titular por identificar",
    "cargas-sociales": "Cargas sociales",
    "bienes-sustitutos": "Bienes Sustitutos",
    "otros-impuestos": "Otros impuestos",
    "por-identificar": "Por identificar",
}
ZERO = Decimal(0)


class ConflictoVersion(ValueError):
    pass


def normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto or "") if not unicodedata.combining(c)).lower()


def clasificar(fila):
    texto = normalizar(fila.get("detalle"))
    if fila["origen"] == "Ret. IVA Granos":
        return "iva"
    if "autonom" in texto:
        if "lucy" in texto or fila.get("idSocio") == 2:
            return "autonomos-lucy"
        if "sergio" in texto or fila.get("idSocio") == 1:
            return "autonomos-sergio"
        return "autonomos-pendientes"
    if ("sicore" in texto and ("gananc" in texto or "217" in texto)) or (fila["origen"] == "Impuestos" and "retenc" in texto and "gananc" in texto):
        return "sicore-ganancias"
    if "gananc" in texto:
        return "ganancias"
    if "cargas sociales" in texto or "f931" in texto.replace(" ", "").replace(".", "") or texto.startswith(("art ", "renatea ", "renatre ")):
        return "cargas-sociales"
    if "bienes sociedad" in texto or "bienes sustit" in texto or "bp-acciones" in texto:
        return "bienes-sustitutos"
    if fila["origen"] == "Impuestos":
        if texto.startswith("iva ") or texto == "iva":
            return "iva"
        return "otros-impuestos"
    # No atribuir una anulación bancaria ni un VEP genérico al IVA.
    return "por-identificar"


def decimal(valor):
    return Decimal(str(valor or 0))


def validar_partes(partes, deuda, credito):
    if not partes:
        return
    claves = set()
    for p in partes:
        if p["subcuenta"] not in CATALOGO or p["subcuenta"] in claves:
            raise ValueError("Subcuenta inválida o repetida en el reparto")
        claves.add(p["subcuenta"])
        for campo in ("deuda", "credito"):
            valor = decimal(p[campo])
            if not valor.is_finite() or valor < 0 or valor != valor.quantize(Decimal("0.0001")):
                raise ValueError("Importes no negativos, con hasta cuatro decimales")
        if decimal(p["deuda"]) == 0 and decimal(p["credito"]) == 0:
            raise ValueError("Una parte del reparto debe tener importe")
    if sum(decimal(p["deuda"]) for p in partes) != decimal(deuda) or sum(decimal(p["credito"]) for p in partes) != decimal(credito):
        raise ValueError("El reparto debe sumar exactamente la deuda y el crédito del movimiento original")


def cargar():
    from src.features.cuentas_corrientes.arca_documentos import por_movimiento
    filas = read("""
        SELECT b.Fecha fecha,b.Documento documento,b.[Nro Documento] numeroDocumento,
          b.Deuda deuda,b.Credito credito,b.Origen origen,b.IdOrigen idOrigen,
          COALESCE(t.[Nombre Impuesto] + ' ' + ISNULL(i.[Periodo liquidado],''),
            g.[Descripción] + ' ' + ISNULL(g.[Observaciones Cliente],''),
            n.Concepto,s.Motivo,e.Caja,'') detalle,s.IdSocio idSocio
        FROM dbo.vw_MovimientosCuenta_Base b
        LEFT JOIN dbo.Impuestos i ON b.Origen='Impuestos' AND i.IdImpuesto=b.IdOrigen
        LEFT JOIN dbo.[Tipo Impuesto] t ON t.IdTipoImpuesto=i.IdTipoImpuesto
        LEFT JOIN dbo.[Movimientos Galicia] g ON b.Origen='Galicia' AND g.IdMovimiento=b.IdOrigen
        LEFT JOIN dbo.[Movimientos BNA] n ON b.Origen='Banco Nacion' AND n.IdMovimientoBNA=b.IdOrigen
        LEFT JOIN dbo.MovimientosCuentaSocio s ON b.Origen='Pago por socio' AND s.IdMovimiento=b.IdOrigen
        LEFT JOIN dbo.vw_PagosEfectivoVigentes e ON b.Origen='Pagos efectivo' AND e.IdPagoEfectivo=b.IdOrigen
        WHERE b.IdContacto=119 ORDER BY b.Fecha,b.Origen,b.IdOrigen
    """)
    marcas = read("""SELECT IdClasificacion version,Origen origen,IdOrigen idOrigen,Reparto reparto,Motivo motivo,
        Usuario usuario,Fecha fecha FROM (SELECT *,ROW_NUMBER() OVER
        (PARTITION BY Origen,IdOrigen ORDER BY IdClasificacion DESC) rn FROM dbo.ArcaClasificaciones) q WHERE rn=1""")
    documentos = por_movimiento()
    for f in filas:
        f["documentos"] = documentos.get((f["origen"], f["idOrigen"]), [])
    return filas, {(m["origen"], m["idOrigen"]): m for m in marcas}


def construir(filas, marcas, desde=None, hasta=None, subcuenta=None, page=1, size=50):
    resumen = {k: {"clave": k, "nombre": v, "deuda": ZERO, "credito": ZERO, "saldo": ZERO, "cantidad": 0} for k, v in CATALOGO.items()}
    apertura, acumulado = ZERO, ZERO
    items = []
    vistos = set()
    for f in filas:
        fecha = f["fecha"].date() if hasattr(f["fecha"], "hour") else f["fecha"]
        if isinstance(fecha, str):
            fecha = date.fromisoformat(fecha[:10])
        if hasta and fecha > hasta:
            continue
        key = (f["origen"], f["idOrigen"])
        if key in vistos:
            raise ValueError("El origen identifica varias filas de ARCA; revisar antes de repartir")
        vistos.add(key)
        marca = marcas.get(key, {})
        manual = json.loads(marca.get("reparto") or "[]")
        desactualizada = False
        try:
            validar_partes(manual, f["deuda"], f["credito"])
        except ValueError:
            # El original puede corregirse en su módulo. No ocultar la cuenta ni
            # conservar un reparto que ya no suma; pedir nueva clasificación.
            manual, desactualizada = [], True
        if desactualizada:
            partes = [{"subcuenta": "por-identificar", "deuda": decimal(f["deuda"]), "credito": decimal(f["credito"])}]
        else:
            partes = manual or [{"subcuenta": clasificar(f), "deuda": decimal(f["deuda"]), "credito": decimal(f["credito"])}]
        for p in partes:
            r = resumen[p["subcuenta"]]
            r["deuda"] += decimal(p["deuda"])
            r["credito"] += decimal(p["credito"])
            r["saldo"] = r["credito"] - r["deuda"]
            r["cantidad"] += 1
        seleccion = [p for p in partes if not subcuenta or p["subcuenta"] == subcuenta]
        if not seleccion:
            continue
        deuda = sum((decimal(p["deuda"]) for p in seleccion), ZERO)
        credito = sum((decimal(p["credito"]) for p in seleccion), ZERO)
        acumulado += credito - deuda
        if desde and fecha < desde:
            apertura = acumulado
            continue
        items.append({**f, "fecha": fecha, "deuda": deuda, "credito": credito,
                      "deudaOriginal": decimal(f["deuda"]), "creditoOriginal": decimal(f["credito"]),
                      "partes": partes, "version": marca.get("version", 0), "manual": bool(manual),
                      "motivo": marca.get("motivo"), "revisarReparto": desactualizada, "saldo": acumulado})
    inicio = (page - 1) * size
    return {"resumen": list(resumen.values()), "saldoTotal": sum((r["saldo"] for r in resumen.values()), ZERO),
            "apertura": apertura, "saldoSeleccion": acumulado, "items": items[inicio:inicio + size],
            "total": len(items), "page": page, "pageSize": size}


def cuenta(desde=None, hasta=None, subcuenta=None, page=1, size=50):
    if desde and hasta and desde > hasta:
        raise ValueError("La fecha desde debe ser anterior o igual a la fecha hasta")
    if subcuenta and subcuenta not in CATALOGO:
        raise ValueError("Subcuenta desconocida")
    filas, marcas = cargar()
    return construir(filas, marcas, desde, hasta, subcuenta, page, size)


@atomic_reconciliation
def guardar(origen, id_origen, version, partes, motivo, usuario):
    filas = read("SELECT Deuda deuda,Credito credito FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=119 AND Origen=? AND IdOrigen=?", (origen, id_origen))
    if not filas:
        raise LookupError("El movimiento no pertenece a ARCA")
    if len(filas) != 1:
        raise ValueError("El origen identifica más de un movimiento")
    validar_partes(partes, filas[0]["deuda"], filas[0]["credito"])
    actual = read("SELECT TOP (1) IdClasificacion version FROM dbo.ArcaClasificaciones WHERE Origen=? AND IdOrigen=? ORDER BY IdClasificacion DESC", (origen, id_origen))
    if (actual[0]["version"] if actual else 0) != version:
        raise ConflictoVersion("La clasificación cambió. Actualizá la cuenta antes de guardar")
    nueva = execute_insert_returning_id("""INSERT INTO dbo.ArcaClasificaciones
        (Origen,IdOrigen,Reparto,Motivo,Usuario) OUTPUT INSERTED.IdClasificacion VALUES (?,?,?,?,?)""",
        (origen, id_origen, json.dumps(partes, default=str, ensure_ascii=False), motivo.strip(), usuario))
    return {"version": nueva}
