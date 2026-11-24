"""Lector de Liquidaciones Primarias de Granos (LPG, formato estándar de ARCA) y de certificados de retención de IVA de
granos (24/11/2026, pedido de Sergio: carga automática y lista para revisar).

  · `leer_lpg(texto)`: datos del PDF (COE, comprador, grano, grado, factor, kilos, precio y flete por tonelada,
    alícuota de IVA, deducciones, retenciones y neto impreso).
  · `cargar_lpg(pdf, ruta, ...)`: da de alta la venta de granos si el neto calculado por el sistema cierra al centavo con
    el impreso; si no, la deja para cargar a mano con el motivo. Devuelve el dict de la bóveda
    `{estadoCarga, motivo, idRegistro, numeroDocumento, totalImpreso}`.
  · Tipo de cambio: el del portal si lo trae (dolarRate > 1); si no, dólar BNA comprador divisa del día hábil anterior
    a la fecha de la liquidación (regla de Sergio 21/10/2026, verificada: 66 de 69 LPG de Cargill con TC en el portal;
    las 3 restantes son dólar soja 09/2022).
  · `aplicar_certificado(pdf, ruta)`: certificado de retención de IVA de una LPG («Nro de comprobante origen» = COE):
    una fila en [Retenciones IVA Granos]; la venta queda igual a la LPG (retención aparte, Sergio 24/11/2026).
"""

from __future__ import annotations

import io
import logging
import re
from datetime import date, datetime, timedelta

from src.db.connection import execute_write_transaction, fetch_all, fetch_one

log = logging.getLogger(__name__)

GIAMIGLI = "30712114602"
TIPO_DOC_LIQUIDACION = 6
CONCEPTO_GASTOS, CONCEPTO_OTRAS = 1, 2
TOLERANCIA = 0.05  # $: el neto del sistema contra el impreso
# Código de grano ARCA → producto de Ventas de granos (Granos). La soja se toma como de primera: si la campaña tuvo
# también soja de segunda, la venta queda marcada para revisar el grano.
GRANO_ARCA = {"19": "Maiz", "23": "Soja primera", "2": "Trigo", "15": "Trigo", "1": "Trigo", "3": "Cebada",
              "6": "Sorgo", "26": "Sorgo", "13": "Girasol", "4": "Avena"}
# Variante del mismo grano (DestinoCompras de Datos Cosecha). El maíz diferido en general se consume con la hacienda
# (Sergio 24/11/2026): la venta va a la variante que se cosechó en la campaña; si se cosecharon las dos, a la principal
# con aviso para revisar.
ALTERNATIVA = {"Maiz": "Maiz diferido", "Soja primera": "Soja segunda"}
INVIERNO = {"Trigo", "Cebada", "Avena"}


def _texto(pdf: bytes) -> str:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf)) as p:
        return "\n".join((pg.extract_text() or "") for pg in p.pages)


def _num(s: str | None) -> float | None:
    """'5,698,761.96' / '5546,86' / '201.79' / '65682,835' → float."""
    if s is None:
        return None
    s = s.strip().replace("$", "").replace(" ", "")
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(",", "") if s.rfind(".") > s.rfind(",") else s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".") if re.fullmatch(r"-?\d+,\d{1,3}", s) and len(s.split(",")[1]) != 3 else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def es_lpg(texto: str) -> bool:
    return bool(re.search(r"LIQUIDACI.N PRIMARIA DE GRANOS", texto.upper())) and "C.O.E." in texto.upper()


def leer_lpg(texto: str) -> dict | None:
    t = texto
    if not es_lpg(t):
        return None
    m = re.search(r"C\.O\.E\.:\s*(\d{8,})", t)
    coe = m.group(1) if m else None
    m = re.search(r"^(\d{2}/\d{2}/\d{4}),", t, re.M)
    fecha = datetime.strptime(m.group(1), "%d/%m/%Y").date() if m else None
    cuits = [c for c in re.findall(r"C\.U\.I\.T\.:\s*(\d{11})", t) if c != GIAMIGLI]
    m = re.search(r"\$\s*([\d.,]+)\s+(\S+)\s+(\d+)\s*-\s*([A-ZÁÉÍÓÚÑ ]+?)\s+\$\s*([\d.,]+)", t)
    if not (coe and fecha and m):
        return None
    precio_tn, grado_op, cod_grano, nombre_grano, flete_tn = _num(m.group(1)), m.group(2), m.group(3), m.group(4).strip(), _num(m.group(5))
    m2 = re.search(r"Flete:\s*-?\s*([\d.,]+)\$/TN", t)  # más decimales en «Datos adicionales»
    preciso = _num(m2.group(1).replace(".", "").replace(",", ".")) if m2 else None  # «65682,835»: coma decimal
    if preciso and abs(preciso - (flete_tn or 0)) < 1:
        flete_tn = preciso
    m = re.search(r"MERCADER.A ENTREGADA.*?\n.*?\n\s*(\d+)\s+(\S+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+Localidad", t, re.S)
    grado_merc, factor, proteico, kilos_entregados = (m.group(2), _num(m.group(3)), _num(m.group(4)), _num(m.group(5))) if m else (None, 100.0, 0.0, None)
    m = re.search(r"OPERACI.N\s*\n.*?\n\s*([\d.,]+)\s*Kg\s+\$\s*([\d.,]+)\s+\$\s*([\d.,]+)\s+([\d.,]+)\s+\$\s*([\d.,]+)\s+\$\s*([\d.,]+)", t)
    if not m:
        return None
    kilos, subtotal, alicuota, iva, total_op = _num(m.group(1)), _num(m.group(3)), _num(m.group(4)), _num(m.group(5)), _num(m.group(6))

    deducciones = []
    bloque = re.search(r"\nDEDUCCIONES\n(.*?)\nRETENCIONES\n", t, re.S)
    if bloque:
        # El nombre del concepto viene partido alrededor del renglón («HONORARIOS» / renglón / «LABORATORIO»): la línea
        # suelta antes del renglón abre la etiqueta y la que sigue inmediatamente la completa.
        pendientes: list[str] = []
        recien = False
        for ln in bloque.group(1).splitlines()[1:]:  # sin el encabezado de columnas
            d = re.search(r"(Comisi\S* o Gastos Administrativos|Otras Deducciones)\s*(.*?)\$\s*([\d.,]+)\s+([\d.,]+)%\s+"
                          r"\$\s*([\d.,]+)\s+\$\s*([\d.,]+)", ln)
            if d:
                deducciones.append({
                    "idConcepto": CONCEPTO_GASTOS if d.group(1).lower().startswith("comisi") else CONCEPTO_OTRAS,
                    "_etiqueta": " ".join(pendientes), "_propio": d.group(2).strip(), "porc": 100.0,
                    "baseCalculo": _num(d.group(3)), "alicuota": _num(d.group(4)), "_total": _num(d.group(6))})
                pendientes, recien = [], True
            elif ln.strip():
                if recien and deducciones:
                    deducciones[-1]["_etiqueta"] = (deducciones[-1]["_etiqueta"] + " " + ln.strip()).strip()
                    recien = False
                else:
                    pendientes.append(ln.strip())
        for x in deducciones:
            x["detalle"] = (x.pop("_propio") or x["_etiqueta"] or "Deducción").title()[:100]

    def total(rx):
        mm = re.search(rx + r"\s*\$\s*([\d.,]+)", t)
        return _num(mm.group(1)) if mm else 0.0

    contrato = re.search(r"Contrato:\s*(\w+)", t)
    return {
        "coe": coe, "fecha": fecha, "cuitComprador": cuits[0] if cuits else None,
        "precioTn": precio_tn, "gradoOperacion": grado_op, "codigoGrano": cod_grano, "grano": nombre_grano,
        "fleteTn": flete_tn or 0.0, "gradoMercaderia": grado_merc, "factor": factor or 100.0, "proteico": proteico or 0.0,
        "kilosEntregados": kilos_entregados or kilos, "kilos": kilos, "subtotal": subtotal, "alicuotaIVA": alicuota,
        "iva": iva, "totalOperacion": total_op, "deducciones": deducciones,
        "retencionesAfip": total(r"Total Retenciones Afip:"), "otrasRetenciones": total(r"Total Otras Retenciones:"),
        "percepciones": total(r"Total Percepciones:"), "totalDeducciones": total(r"Total Deducciones:"),
        "netoImpreso": total(r"Importe Neto a Pagar:"), "contrato": contrato.group(1) if contrato else None,
    }


# --- datos que el PDF no trae ---------------------------------------------------------------------------------------

def tc_estimado(fecha: date, dolar_rate_portal: float | None = None) -> tuple[float | None, str]:
    if dolar_rate_portal and dolar_rate_portal > 1.01:
        return round(float(dolar_rate_portal), 4), "TC informado por el portal"
    f = fetch_one("SELECT TOP 1 CONVERT(date, Fecha) AS f, Comp_Divisa AS c FROM dbo.[Dolar BNA] "
                  "WHERE Fecha < ? AND Comp_Divisa > 0 ORDER BY Fecha DESC", (fecha,))
    if not f:
        return None, "Sin cotización BNA cargada para estimar el TC"
    return float(f["c"]), f"TC estimado: BNA comprador divisa del {datetime.strptime(str(f['f'])[:10], '%Y-%m-%d'):%d/%m/%Y} (día hábil anterior)"


def campania(grano: str, fecha: date, informada: str | None = None) -> str:
    if informada and re.fullmatch(r"\d{4}/\d{4}", informada.strip()):
        return informada.strip()
    y = fecha.year
    if grano in INVIERNO:  # trigo/cebada: cosecha nov-ene
        return f"{y}/{y + 1}" if fecha.month >= 11 else f"{y - 1}/{y}"
    return f"{y - 1}/{y}" if fecha.month >= 3 else f"{y - 2}/{y - 1}"  # gruesa: cosecha mar-jul, venta en el año


def _id_grano(nombre: str) -> int | None:
    f = fetch_one("SELECT IdGrano AS i FROM dbo.Granos WHERE Grano = ?", (nombre,))
    return int(f["i"]) if f else None


def _cosechado(destino: str, camp: str) -> float:
    f = fetch_one(
        "SELECT SUM(d.[Cantidad a Liquidar]) AS kg FROM dbo.[Datos Cosecha] d JOIN dbo.DestinoCompras dc ON dc.IdDestino = d.IdDestino "
        "JOIN dbo.Campañas ca ON ca.IdCampaña = d.IdCampaña WHERE dc.Destino = ? AND ca.Campaña = ?", (destino, camp))
    return float(f["kg"] or 0) if f else 0.0


def grano_por_cosecha(nombre: str, camp: str) -> tuple[str, str | None]:
    """(grano, aviso). Elige entre la variante principal y la alternativa según lo cosechado en la campaña."""
    alt = ALTERNATIVA.get(nombre)
    if not alt:
        return nombre, None
    kg_pri, kg_alt = _cosechado(nombre, camp), _cosechado(alt, camp)
    if kg_alt and not kg_pri:
        return alt, f"grano {alt}: es lo único cosechado en {camp}"
    if kg_alt and kg_pri:
        return nombre, f"en {camp} también se cosechó {alt} ({kg_alt:,.0f} kg): revisar el grano".replace(",", ".")
    return nombre, None


def _contacto_por_cuit(cuit: str | None) -> int | None:
    if not cuit:
        return None
    f = fetch_one("SELECT TOP 1 IdContacto AS i FROM dbo.Contactos WHERE REPLACE(REPLACE([CUIT/CUIL], '-', ''), ' ', '') = ? "
                  "ORDER BY IdContacto", (cuit,))
    return int(f["i"]) if f else None


# --- alta -------------------------------------------------------------------------------------------------------------

def cargar_lpg(pdf: bytes, ruta: str, *, id_contacto: int | None = None, dolar_rate: float | None = None,
               campania_informada: str | None = None, simular: bool = False) -> dict:
    from src.features.ventas_granos import repository as vg

    res = {"estadoCarga": "pendiente", "motivo": None, "idRegistro": None, "numeroDocumento": None, "totalImpreso": None}
    try:
        d = leer_lpg(_texto(pdf))
    except Exception as e:
        return {**res, "motivo": f"No se pudo leer el PDF: {e.__class__.__name__}"}
    if d is None:
        try:
            if re.search(r"Tipo de operaci.n:\s*Ajuste", _texto(pdf)):
                return {**res, "motivo": "Ajuste de liquidación (bonificación o débito de precio): cargar a mano"}
        except Exception:
            pass
        return {**res, "motivo": "No se reconoció el formato de la liquidación: cargar a mano"}
    res.update(numeroDocumento=d["coe"], totalImpreso=d["netoImpreso"])
    from src.features.boveda import repository as boveda

    ya = boveda.venta_granos_existente(d["coe"])
    if ya:
        return {**res, "estadoCarga": "ya_cargado", "idRegistro": ya["idVenta"]}
    id_contacto = _contacto_por_cuit(d["cuitComprador"]) or id_contacto
    if not id_contacto:
        return {**res, "motivo": f"El comprador (CUIT {d['cuitComprador']}) no está en Contactos: cargar a mano"}
    nombre = GRANO_ARCA.get(d["codigoGrano"]) or d["grano"].title()
    camp = campania(nombre, d["fecha"], campania_informada)
    nombre, aviso_grano = grano_por_cosecha(nombre, camp)
    id_grano = _id_grano(nombre)
    if not id_grano:
        return {**res, "motivo": f"Grano «{d['grano']}» sin equivalente en Ventas de granos: cargar a mano"}
    tc, nota_tc = tc_estimado(d["fecha"], dolar_rate)
    avisos = [nota_tc]
    if not campania_informada:
        avisos.append(f"campaña {camp} estimada por la fecha")
    if aviso_grano:
        avisos.append(aviso_grano)
    if d["retencionesAfip"]:
        avisos.append("la liquidación trae retenciones de ARCA: revisar IVA / Ganancias")

    cabecera = {
        "idConsignatario": id_contacto, "idTipoDocumento": TIPO_DOC_LIQUIDACION, "numeroDocumento": d["coe"],
        "fecha": d["fecha"], "precioUnitario": d["precioTn"], "tipoCambio": tc, "gradoOperacion": d["gradoOperacion"],
        "idProducto": id_grano, "tipoDeGrano": None, "campania": camp, "flete": d["fleteTn"], "nroDeposito": None,
        "gradoMercaderia": d["gradoMercaderia"], "factor": d["factor"], "contProteico": d["proteico"],
        "cantidadEntregada": d["kilosEntregados"], "cantidadVendida": d["kilos"], "alicuotaIVA": d["alicuotaIVA"],
        "retencionIVA": 0.0, "retIG": d["retencionesAfip"], "percepciones": d["percepciones"],
        "otraRetenciones": d["otrasRetenciones"], "sellado": 0.0, "derechoRegistro": 0.0, "honorariosCamara": 0.0,
        "aCuentaCalidad": 0.0, "iibb": 0.0, "documentoOriginal": ruta,
    }
    deducciones = [{k: v for k, v in x.items() if not k.startswith("_")} for x in d["deducciones"]]
    # Cargill redondea el subtotal: la diferencia con kilos × precio/kg va como ajuste (misma convención que los
    # «Redondeo cuenta Cargill (036)» de las ventas ya cargadas), así la venta queda igual al PDF.
    ajustes = []
    sin_ajuste = vg.calcular_totales(cabecera, [], deducciones)
    dif = round((d["subtotal"] or 0) - sin_ajuste["subTotal"], 4)
    if 0.0001 < abs(dif) <= 5:
        ajustes.append({"concepto": "Redondeo LPG", "importe": dif, "alicuotaIVA": 0.0})
    calc = vg.calcular_totales(cabecera, ajustes, deducciones)["importeNetoAPercibir"]
    if abs(calc - (d["netoImpreso"] or 0)) > TOLERANCIA:
        return {**res, "motivo": f"No cierra al centavo: calculado {calc:,.2f}, impreso {d['netoImpreso']:,.2f}. Cargar a mano"}
    if simular:
        return {**res, "estadoCarga": "cargado_auto", "motivo": "Simulación: " + "; ".join(avisos), "cabecera": cabecera,
                "deducciones": deducciones, "ajustes": ajustes}
    try:
        id_venta = vg.create_venta(cabecera, ajustes, deducciones)
    except Exception as e:
        return {**res, "motivo": f"El alta de Ventas de granos lo rechazó: {e}"}
    aplicar_certificados_guardados(d["coe"])
    return {**res, "estadoCarga": "cargado_auto", "idRegistro": id_venta, "motivo": "; ".join(avisos)}


# --- certificados de retención de IVA ---------------------------------------------------------------------------------

def leer_certificado(texto: str) -> dict | None:
    u = texto.upper()
    if "CERTIFICADO DE RETENCI" not in u or "IVA" not in u or "LIQUIDACION PRIMARIA DE GRANOS" not in u.replace("Ó", "O"):
        return None
    nro = re.search(r"Nro:\s*([\d-]+)", texto)
    coe = re.search(r"comprobante origen:\s*(\d{8,})", texto, re.I)
    imp = re.search(r"Importe Retenido:\s*\$\s*([\d.,]+)", texto)
    cuit = re.search(r"AGENTE DE RETENCION\s*\n\s*C\.U\.I\.T:\s*([\d-]+)", texto)
    if not (nro and coe and imp):
        return None
    importe = _num(imp.group(1).replace(".", "").replace(",", ".")) if "," in imp.group(1) else _num(imp.group(1))
    return {"nro": nro.group(1), "coe": coe.group(1), "importe": importe,
            "cuitAgente": re.sub(r"\D", "", cuit.group(1)) if cuit else None}


def aplicar_certificado(pdf: bytes, ruta: str) -> dict:
    """Asocia el certificado a su venta. `{estadoCarga, motivo, idRegistro, numeroDocumento, totalImpreso}`."""
    res = {"estadoCarga": "pendiente", "motivo": None, "idRegistro": None, "numeroDocumento": None, "totalImpreso": None}
    try:
        c = leer_certificado(_texto(pdf))
    except Exception as e:
        return {**res, "motivo": f"No se pudo leer el PDF: {e.__class__.__name__}"}
    if c is None:
        return {**res, "motivo": "Revisar y cargar a mano"}
    res.update(numeroDocumento=c["nro"], totalImpreso=c["importe"])
    return {**res, **_asociar(c, ruta)}


def _asociar(c: dict, ruta: str) -> dict:
    from src.features.boveda import repository as boveda

    venta = boveda.venta_granos_existente(c["coe"])
    if not venta:
        return {"motivo": f"Retención de la liquidación {c['coe']}, que todavía no está cargada: se asocia sola al cargarla"}
    if fetch_one("SELECT 1 AS x FROM dbo.[Retenciones IVA Granos] WHERE [Nro Certificado] = ?", (c["nro"],)):
        return {"estadoCarga": "ya_cargado", "idRegistro": venta["idVenta"]}
    agente = _contacto_por_cuit(c["cuitAgente"]) or fetch_one(
        "SELECT IdConsignatario AS i FROM dbo.[Venta Granos] WHERE IdVenta = ?", (venta["idVenta"],))["i"]
    siguiente = fetch_one("SELECT ISNULL(MAX(IdRetencion), 0) + 1 AS n FROM dbo.[Retenciones IVA Granos]")["n"]
    # 24/11/2026 (Sergio): la retención va APARTE de la venta, que queda igual a la LPG. El certificado entra a la cuenta
    # del agente como «Retención IVA granos» y a la de AFIP como crédito (vw_CnsRetencionesIVAGranos).
    execute_write_transaction([
        ("INSERT INTO dbo.[Retenciones IVA Granos] (IdRetencion, IdLiquidacion, [Nro Certificado], [Agente Retencion], "
         "[Importe Retenido], [Importe Devolucion], Imagen) VALUES (?, ?, ?, ?, ?, ?, ?)",
         (siguiente, venta["idVenta"], c["nro"], agente, c["importe"], c["importe"], ruta)),
    ])
    return {"estadoCarga": "cargado_auto", "idRegistro": venta["idVenta"],
            "motivo": f"Retención de IVA de la liquidación {c['coe']} registrada aparte (crédito con ARCA)"}


def aplicar_certificados_guardados(coe: str) -> int:
    """Al cargar una LPG: certificados ya bajados que esperaban esa liquidación (bajan antes o en la misma corrida)."""
    n = 0
    for d in fetch_all("SELECT IdDocumentoNuevo AS id, Ruta AS r FROM dbo.DocumentosNuevos WHERE Tipo = 'retencion' "
                       "AND Estado = 'para_cargar' AND Motivo LIKE ?", (f"%{coe}%",)):
        try:
            with open(d["r"], "rb") as fh:
                c = leer_certificado(_texto(fh.read()))
            if c and c["coe"] == coe:
                r = _asociar(c, d["r"])
                if r.get("estadoCarga") in ("cargado_auto", "ya_cargado"):
                    from src.db.connection import execute_write

                    execute_write("UPDATE dbo.DocumentosNuevos SET Estado = 'cargado_solo', Modulo = 'granos', IdRegistro = ?, "
                                  "Motivo = ? WHERE IdDocumentoNuevo = ?", (r["idRegistro"], r.get("motivo"), d["id"]))
                    n += 1
        except Exception:
            log.exception("LPG %s: no se pudo asociar el certificado %s", coe, d["id"])
    return n
