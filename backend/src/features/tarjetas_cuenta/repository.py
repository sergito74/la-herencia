"""Lectura de la cuenta de cada tarjeta sobre `vw_MovimientosCuenta_Base` — 034.

Solo lectura salvo `cruces.py`. Las ramas de la vista (consumos, cargos,
devoluciones, pagos sin movimiento y Mercado Pago) las crea
`scripts/vista_tarjeta_cuenta_corriente.py`. El saldo es `crédito − deuda`
(negativo = se debe), el mismo criterio de toda la vista.

Las funciones puras (`construir_filas`, `agrupar_por_resumen`, `acumular`,
`detalle_saldo`) se prueban con fixtures; las que consultan la base (`cargar_*`,
`resumen_tarjetas`, `cuenta_tarjeta`) solo leen.
"""

from __future__ import annotations

from datetime import date, datetime

from src.db.connection import fetch_all, fetch_one
from src.features.tarjetas import repository as tarjetas_repository
from src.features.tarjetas.compensaciones import get_compensaciones

ORIGEN_FILA = {"Tarjeta consumo": "Consumo", "Tarjeta cargo": "Cargo del resumen", "Tarjeta devolución": "Devolución"}
# Origen de la vista -> valor de `Tarjetas_Resumenes_Pagos.Origen` / medio de Tesorería.
PAGOS_ORIGEN_POR_VISTA = {"Banco Nacion": "BNA", "Galicia": "Galicia"}
MEDIO_POR_ORIGEN = {"Banco Nacion": "bna", "Galicia": "galicia", "Pagos efectivo": "efectivo"}
TOLERANCIA_VINCULO = 0.01


def _dia(valor) -> date | None:
    if valor is None:
        return None
    return valor.date() if isinstance(valor, datetime) else valor


# --------------------------------------------------------------------------- funciones puras

def estado_vinculo(importe: float, vinculado: float, tiene_proveedor: bool, cruzado: bool) -> str:
    if cruzado:
        return "cruzado-con-devolucion"
    if abs(importe - vinculado) <= TOLERANCIA_VINCULO:
        return "vinculado"
    return "resto-con-proveedor" if tiene_proveedor else "sin-proveedor"


def construir_filas(
    vista: list[dict],
    consumos: dict[int, dict],
    pagos_resumen: dict[tuple[str, int], int],
    pagos_sin_movimiento: dict[int, int],
    codigos: dict[int, str] | None = None,
) -> list[dict]:
    """Convierte las filas de la vista del contacto de la tarjeta en filas de la cuenta.

    `vista`: filas de `vw_MovimientosCuenta_Base` ya ordenadas por (Fecha, Origen, IdOrigen).
    `consumos`: info por `IdLineaConsumo` (idResumen, detalle, proveedor, importe, vinculado, tieneProveedor, cruzado).
    `pagos_resumen`: (Origen de `Tarjetas_Resumenes_Pagos`, IdMovimientoOrigen) -> IdResumen.
    `pagos_sin_movimiento`: IdPago -> IdResumen.
    """
    codigos = codigos or {}
    filas = []
    for v in vista:
        origen_vista, id_origen = v["Origen"], int(v["IdOrigen"])
        deuda, credito = float(v["Deuda"] or 0), float(v["Credito"] or 0)
        fila = {
            "fecha": _dia(v["Fecha"]), "origen": ORIGEN_FILA.get(origen_vista, "Pago"),
            "idResumen": None, "codigo": v.get("nro"), "detalle": None, "proveedor": None,
            "deuda": deuda, "credito": credito, "estadoVinculo": None, "referencia": None,
            "_origenVista": origen_vista, "_idOrigen": id_origen,
        }
        if origen_vista == "Tarjeta consumo":
            info = consumos.get(id_origen, {})
            fila.update(idResumen=info.get("idResumen"), detalle=info.get("detalle"), proveedor=info.get("proveedor"),
                        estadoVinculo=estado_vinculo(info.get("importe", deuda - credito), info.get("vinculado", 0.0),
                                                     bool(info.get("tieneProveedor")), bool(info.get("cruzado"))),
                        referencia={"tipo": "linea-consumo", "idLineaConsumo": id_origen, "idResumen": info.get("idResumen")})
        elif origen_vista == "Tarjeta cargo":
            id_resumen = id_origen // 100
            fila.update(idResumen=id_resumen, detalle=v.get("Documento"),
                        codigo=v.get("nro") or codigos.get(id_resumen),
                        referencia={"tipo": "resumen", "idResumen": id_resumen})
        elif origen_vista == "Tarjeta devolución":
            fila.update(detalle="Devolución de débito cruzada con su pago", referencia={"tipo": "cruce", "idCruce": id_origen})
        elif origen_vista == "Tarjeta pago":
            id_resumen = pagos_sin_movimiento.get(id_origen)
            fila.update(idResumen=id_resumen, detalle="Pago de resumen sin movimiento bancario de origen",
                        referencia={"tipo": "resumen", "idResumen": id_resumen})
        else:
            medio = MEDIO_POR_ORIGEN.get(origen_vista)
            id_resumen = pagos_resumen.get((PAGOS_ORIGEN_POR_VISTA.get(origen_vista, origen_vista), id_origen))
            fila.update(idResumen=id_resumen, detalle=v.get("Documento"),
                        referencia={"tipo": "movimiento-bancario", "medio": medio, "idMovimiento": id_origen,
                                    "idResumen": id_resumen} if medio else None)
        filas.append(fila)
    return filas


def agrupar_por_resumen(filas: list[dict], cierres: dict[int, date], codigos: dict[int, str]) -> list[dict]:
    """Una fila por resumen (consumos y cargos sumados) más las filas de pagos y devoluciones."""
    por_resumen: dict[int, dict] = {}
    resto = []
    for f in filas:
        if f["origen"] in ("Consumo", "Cargo del resumen") and f["idResumen"] is not None:
            g = por_resumen.setdefault(f["idResumen"], {"deuda": 0.0, "credito": 0.0})
            g["deuda"] += f["deuda"]
            g["credito"] += f["credito"]
        else:
            resto.append(f)
    grupos = []
    for id_resumen, g in por_resumen.items():
        neto = round(g["deuda"] - g["credito"], 2)
        grupos.append({
            "fecha": cierres.get(id_resumen), "origen": "Resumen", "idResumen": id_resumen,
            "codigo": codigos.get(id_resumen), "detalle": "Consumos y cargos del resumen", "proveedor": None,
            "deuda": neto if neto > 0 else 0.0, "credito": -neto if neto < 0 else 0.0,
            "estadoVinculo": None, "referencia": {"tipo": "resumen", "idResumen": id_resumen},
            "_origenVista": "Resumen", "_idOrigen": id_resumen,
        })
    todas = grupos + resto
    todas.sort(key=lambda f: (f["fecha"] or date.min, 0 if f["origen"] == "Resumen" else 1, f["_idOrigen"]))
    return todas


def acumular(filas: list[dict], desde: date | None, hasta: date | None) -> tuple[float, list[dict], float]:
    """(saldo inicial del período, filas del período con saldo acumulado, saldo final)."""
    saldo = 0.0
    saldo_inicial = 0.0
    periodo = []
    for f in filas:
        if hasta is not None and f["fecha"] is not None and f["fecha"] > hasta:
            continue
        saldo = round(saldo + f["credito"] - f["deuda"], 4)
        if desde is not None and f["fecha"] is not None and f["fecha"] < desde:
            saldo_inicial = saldo
            continue
        periodo.append({**f, "saldo": saldo})
    saldo_inicial = round(saldo_inicial, 2)
    return saldo_inicial, periodo, round(saldo, 2)


def detalle_saldo(filas: list[dict], cierres: dict[int, date], hasta: date, saldo_final: float) -> dict:
    """FR-023: parte del saldo que es consumo aún no resumido (resumen que cierra después de `hasta`)."""
    no_resumido = 0.0
    for f in filas:
        if f["origen"] != "Consumo" or f["idResumen"] is None:
            continue
        if f["fecha"] is not None and f["fecha"] > hasta:
            continue
        cierre = cierres.get(f["idResumen"])
        if cierre is not None and cierre > hasta:
            no_resumido += f["credito"] - f["deuda"]
    no_resumido = round(no_resumido, 2)
    return {"exigible": round(saldo_final - no_resumido, 2), "noResumido": no_resumido}


# --------------------------------------------------------------------------- lectura de la base

def _contactos_anteriores() -> dict[int, dict]:
    if fetch_one("SELECT OBJECT_ID('dbo.TarjetasContacto', 'U') AS t", ())["t"] is None:
        return {}
    filas = fetch_all(
        "SELECT tc.IdTarjeta AS idTarjeta, tc.IdContactoAnterior AS idContactoAnterior, c.[Razon Social] AS contactoAnterior "
        "FROM dbo.TarjetasContacto tc LEFT JOIN dbo.Contactos c ON c.IdContacto = tc.IdContactoAnterior", ())
    return {f["idTarjeta"]: f for f in filas}


def cuotas_a_vencer(id_tarjeta: int) -> list[dict]:
    """FR-015. El cronograma de cuotas (`Cuotas Tarjetas de Credito`) se relaciona con el proveedor de
    cada compra y no registra con qué tarjeta se pagó, por lo que hoy no se pueden atribuir cuotas
    futuras a una tarjeta. Hoy tampoco hay cuotas pendientes (las 183 están cobradas, la última venció
    el 01/12/2016): la sección queda vacía hasta que el cronograma registre la tarjeta."""
    return []


def resumen_tarjetas(hasta: date | None = None) -> dict:
    hoy = date.today()
    corte = hasta or hoy
    tarjetas = tarjetas_repository.get_tarjetas(False)
    contactos = {t["idTarjeta"]: tarjetas_repository.get_id_contacto_tarjeta(t["idTarjeta"]) for t in tarjetas}
    ids = [c for c in contactos.values() if c is not None]
    saldos: dict[int, dict] = {}
    if ids:
        marcas = ",".join("?" * len(ids))
        for f in fetch_all(
            f"SELECT IdContacto AS c, SUM(ISNULL(Deuda,0)) AS deuda, SUM(ISNULL(Credito,0)) AS credito, MAX(Fecha) AS ultimo "
            f"FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto IN ({marcas}) AND Fecha <= ? GROUP BY IdContacto",
            (*ids, datetime.combine(corte, datetime.max.time().replace(microsecond=0)))):
            saldos[f["c"]] = f
    salida, sin_contacto = [], []
    for t in tarjetas:
        contacto = contactos[t["idTarjeta"]]
        if contacto is None:
            sin_contacto.append({"idTarjeta": t["idTarjeta"], "tarjeta": t["nombre"], "motivo": "La tarjeta no tiene contacto asociado"})
            continue
        s = saldos.get(contacto, {"deuda": 0, "credito": 0, "ultimo": None})
        deuda, credito = round(float(s["deuda"] or 0), 2), round(float(s["credito"] or 0), 2)
        saldo = round(credito - deuda, 2)
        pendiente = round(sum(v["saldoPendiente"] for v in get_compensaciones(t["idTarjeta"]).values()), 2)
        salida.append({
            "idTarjeta": t["idTarjeta"], "tarjeta": t["nombre"], "banco": t.get("banco"), "activa": bool(t["activa"]),
            "idContacto": contacto, "deuda": deuda, "credito": credito, "saldo": saldo, "pendienteNeto": pendiente,
            "diferenciaConModuloTarjetas": round(abs(saldo + pendiente), 2) if corte >= hoy else None,
            "ultimoMovimiento": _dia(s["ultimo"]), "cuotasAVencer": len(cuotas_a_vencer(t["idTarjeta"])),
        })
    total = {"deuda": round(sum(t["deuda"] for t in salida), 2), "credito": round(sum(t["credito"] for t in salida), 2)}
    total["saldo"] = round(total["credito"] - total["deuda"], 2)
    return {"hasta": corte, "tarjetas": salida, "total": total, "tarjetasSinContacto": sin_contacto}


def _cargar_vista(id_contacto: int, hasta: date | None) -> list[dict]:
    condicion, params = "", [id_contacto]
    if hasta is not None:
        condicion = " AND Fecha <= ?"
        params.append(datetime.combine(hasta, datetime.max.time().replace(microsecond=0)))
    return fetch_all(
        "SELECT Fecha, Documento, [Nro Documento] AS nro, Deuda, Credito, Origen, IdOrigen "
        f"FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ?{condicion} ORDER BY Fecha, Origen, IdOrigen",
        tuple(params))


def _cargar_consumos(id_tarjeta: int) -> dict[int, dict]:
    filas = fetch_all(
        """
        SELECT l.IdLineaConsumo AS id, l.IdResumen AS idResumen, l.Detalle AS detalle, l.NroDocumento AS nroDocumento,
               l.Importe AS importe, l.IdContacto AS idContactoLinea, c.[Razon Social] AS proveedorLinea,
               ISNULL((SELECT SUM(v.ImporteImputado) FROM dbo.Tarjetas_Resumenes_Lineas_Compras v
                       WHERE v.IdLineaConsumo = l.IdLineaConsumo), 0) AS vinculado,
               (SELECT TOP 1 ct.[Razon Social] FROM dbo.Tarjetas_Resumenes_Lineas_Compras v
                  JOIN dbo.Compras cm ON cm.IdDeuda = v.IdCompra JOIN dbo.Contactos ct ON ct.IdContacto = cm.IdContacto
                 WHERE v.IdLineaConsumo = l.IdLineaConsumo ORDER BY v.IdVinculo) AS proveedorVinculo,
               CASE WHEN OBJECT_ID('dbo.TarjetasCruces', 'U') IS NOT NULL AND EXISTS (
                      SELECT 1 FROM dbo.TarjetasCruces x WHERE x.Tipo = 'consumo-devolucion'
                        AND x.IdLineaConsumo = l.IdLineaConsumo AND x.Deshecho = 0) THEN 1 ELSE 0 END AS cruzado
        FROM dbo.Tarjetas_Resumenes_Lineas l
        JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = l.IdResumen
        LEFT JOIN dbo.Contactos c ON c.IdContacto = l.IdContacto
        WHERE r.IdTarjeta = ? AND ISNULL(r.EstadoResumen, '') <> 'Cerrado'
        """, (id_tarjeta,))
    salida = {}
    for f in filas:
        proveedor = f["proveedorVinculo"] or f["proveedorLinea"]
        salida[f["id"]] = {
            "idResumen": f["idResumen"], "detalle": f["detalle"] or f["nroDocumento"], "proveedor": proveedor,
            "importe": float(f["importe"] or 0), "vinculado": float(f["vinculado"] or 0),
            "tieneProveedor": f["idContactoLinea"] is not None, "cruzado": bool(f["cruzado"]),
        }
    return salida


def _cargar_resumenes(id_tarjeta: int) -> tuple[dict[int, date], dict[int, str]]:
    filas = fetch_all("SELECT IdResumen AS id, ResumenCodigo AS codigo, FechaCierre AS cierre FROM dbo.Tarjetas_Resumenes WHERE IdTarjeta = ?", (id_tarjeta,))
    return {f["id"]: _dia(f["cierre"]) for f in filas}, {f["id"]: f["codigo"] for f in filas}


def _cargar_pagos(id_tarjeta: int) -> tuple[dict[tuple[str, int], int], dict[int, int]]:
    filas = fetch_all(
        "SELECT p.IdPago AS idPago, p.Origen AS origen, p.IdMovimientoOrigen AS idMov, p.IdResumen AS idResumen "
        "FROM dbo.Tarjetas_Resumenes_Pagos p JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = p.IdResumen WHERE r.IdTarjeta = ? "
        "ORDER BY p.IdPago", (id_tarjeta,))
    con_movimiento: dict[tuple[str, int], int] = {}
    sin_movimiento: dict[int, int] = {}
    for f in filas:
        if f["idMov"] is None:
            sin_movimiento[f["idPago"]] = f["idResumen"]
        else:
            con_movimiento.setdefault((f["origen"], int(f["idMov"])), f["idResumen"])
    return con_movimiento, sin_movimiento


def cuenta_tarjeta(id_tarjeta: int, desde: date | None, hasta: date | None, agrupar: str = "movimientos") -> dict | None:
    tarjeta = tarjetas_repository.get_tarjeta(id_tarjeta)
    if tarjeta is None:
        return None
    contacto = tarjetas_repository.get_id_contacto_tarjeta(id_tarjeta)
    if contacto is None:
        raise LookupError("La tarjeta no tiene contacto asociado")
    corte = hasta or date.today()
    cierres, codigos = _cargar_resumenes(id_tarjeta)
    pagos_resumen, pagos_sin_movimiento = _cargar_pagos(id_tarjeta)
    filas = construir_filas(_cargar_vista(contacto, corte), _cargar_consumos(id_tarjeta), pagos_resumen, pagos_sin_movimiento, codigos)
    _, _, saldo_final_total = acumular(filas, None, corte)
    detalle = detalle_saldo(filas, cierres, corte, saldo_final_total)
    base = agrupar_por_resumen(filas, cierres, codigos) if agrupar == "resumenes" else filas
    saldo_inicial, periodo, saldo_final = acumular(base, desde, corte)
    anterior = _contactos_anteriores().get(id_tarjeta, {})
    return {
        "idTarjeta": id_tarjeta, "tarjeta": tarjeta["nombre"], "idContacto": contacto, "desde": desde, "hasta": hasta,
        "saldoInicial": saldo_inicial, "filas": periodo, "saldoFinal": saldo_final, "detalleSaldo": detalle,
        "cuotasAVencer": cuotas_a_vencer(id_tarjeta),
        "apertura": {"idContactoAnterior": anterior.get("idContactoAnterior"), "contactoAnterior": anterior.get("contactoAnterior"),
                     "informativo": True},
        "generado": datetime.now(),
    }
