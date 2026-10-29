"""Recibos mensuales del estudio: lectura por página, control al centavo y carga sin pagos."""
from __future__ import annotations

import io
import re
from calendar import monthrange
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pdfplumber

from src.db.connection import fetch_all, execute_insert_returning_id, reconciliation_transaction
from src.features.remuneraciones import repository as remuneraciones

CUIT_EMPRESA = "30712114602"
MESES = ("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre")
COLUMNAS = {
    "0010": "Sueldo basico", "0123": "Dia Gremio", "0200": "Antiguedad",
    "0166": "Ajuste No Remunerativo", "0800": "Redondeo", "0300": "Jubilacion",
    "0302": "Ley 19032", "0310": "Obra Social", "0315": "Obra Social Acuerdos",
    "0322": "Aporte Sindical", "0324": "Servicio de Sepelio",
}
DEDUCCIONES = {"0300", "0302", "0310", "0315", "0322", "0324"}
MONTO = r"-?\d[\d.]*,\d{2}"


def numero(s):
    return Decimal(s.replace(".", "").replace(",", "."))


def reconoce(texto: str) -> bool:
    propio = CUIT_EMPRESA in texto.replace("-", "").replace(" ", "")
    return propio and (("C.U.I.T. EMPRESA:" in texto and "SUELDO NETO" in texto) or "Resumen de Sueldos" in texto)


def leer_pagina(texto: str) -> dict:
    empresa = re.search(r"C\.U\.I\.T\. EMPRESA:\s*([\d-]+)", texto)
    if not empresa or empresa[1].replace("-", "") != CUIT_EMPRESA:
        raise ValueError("El recibo no corresponde a Giamigli")
    cab = re.search(r"^Mensual (\d{2}) (\d{4}) (.+?) (\d{8}) \$", texto, re.M)
    cuil = re.search(r"(\d{2}-\d{8}-\d)\s*/", texto)
    neto = re.search(r"SUELDO NETO \$ (" + MONTO + r")", texto)
    if not cab or not cuil or not neto:
        raise ValueError("No se reconoce el empleado, período o neto del recibo")
    mes, anio = int(cab[1]), int(cab[2])
    if not 1 <= mes <= 12:
        raise ValueError("Mes inválido")
    valores, suma = {}, Decimal("0")
    for codigo, resto in re.findall(r"^(\d{4}) (.+)$", texto, re.M):
        montos = re.findall(MONTO, resto)
        if codigo not in COLUMNAS or not montos:
            raise ValueError(f"Concepto de sueldo sin reconocer: {codigo}")
        valor = numero(montos[-1])
        if (codigo in DEDUCCIONES and valor > 0) or (codigo not in DEDUCCIONES and valor < 0):
            raise ValueError(f"Signo no reconocido en el concepto {codigo}")
        columna = COLUMNAS[codigo]
        valores[columna] = valores.get(columna, Decimal("0")) + abs(valor)
        suma += valor
    if not valores or suma != numero(neto[1]):
        raise ValueError("Los conceptos del recibo no cierran al centavo contra el neto")
    return {"cuil": cuil[1].replace("-", ""), "nombre": cab[3], "mes": mes, "anio": anio,
            "periodo": f"{MESES[mes-1]} {anio}", "neto": suma, "valores": valores,
            # Fecha de devengamiento, convención del importador histórico; no acredita un pago.
            "fecha": datetime(anio, mes, monthrange(anio, mes)[1])}


def leer(pdf: bytes) -> list[dict]:
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        if not 1 <= len(doc.pages) <= 50:
            raise ValueError("Cantidad de páginas de recibos fuera de lo esperado")
        recibos = [dict(leer_pagina(p.extract_text() or ""), pagina=i) for i, p in enumerate(doc.pages)]
        if len({r["periodo"] for r in recibos}) != 1:
            raise ValueError("El paquete contiene períodos distintos")
        return recibos


def empleados_y_existentes(recibos: list[dict]) -> list[dict]:
    preparados, vistos = [], set()
    for recibo in recibos:
        personas = fetch_all("SELECT IdContacto AS id, [Razon Social] AS nombre FROM dbo.Contactos "
                             "WHERE [Tipo Contacto] = 'Empleado' AND "
                             "REPLACE(REPLACE([CUIT/CUIL], '-', ''), ' ', '') = ?", (recibo["cuil"],))
        if len(personas) != 1:
            raise ValueError(f"No se identifica un único empleado para {recibo['nombre']}")
        persona = personas[0]
        clave = (persona["id"], recibo["mes"], recibo["anio"])
        if clave in vistos:
            raise ValueError("El PDF contiene más de un recibo mensual para la misma persona")
        vistos.add(clave)
        # Reconoce también el período heredado dd/mm/aaaa. No elimina ni pisa diferencias.
        filas = fetch_all("SELECT IdSalario AS id, [Periodo liquidado] AS periodo, "
                          + remuneraciones._IMPORTE_SQL + " AS neto FROM dbo.Remuneraciones r "
                          "WHERE IdContacto = ? AND ([Periodo liquidado] = ? OR [Periodo liquidado] LIKE ?)",
                          (persona["id"], recibo["periodo"], f"%/{recibo['mes']:02d}/{recibo['anio']}"))
        if len(filas) > 1 or (filas and Decimal(str(filas[0]["neto"])).quantize(Decimal("0.01")) != recibo["neto"]):
            raise ValueError(f"Hay una liquidación distinta o duplicada de {persona['nombre']} para {recibo['periodo']}")
        preparados.append({**recibo, "contacto": persona["id"], "empleado": persona["nombre"],
                           "existente": filas[0]["id"] if filas else None})
    return preparados


def cargar(pdf: bytes, ruta_paquete: str) -> dict:
    """El llamador guarda el paquete original; los recibos individuales nunca pisan archivos existentes."""
    import pypdfium2 as pdfium

    recibos = leer(pdf)
    with reconciliation_transaction():
        preparados = empleados_y_existentes(recibos)
        nuevos = 0
        with pdfium.PdfDocument(pdf) as origen:
            for r in preparados:
                nombre = remuneraciones.nombre_archivo_recibo(r["fecha"], r["empleado"])
                carpeta = Path(remuneraciones.CARPETA_RECIBOS) / str(r["anio"])
                carpeta.mkdir(parents=True, exist_ok=True)
                destino = carpeta / nombre
                if destino.exists():
                    # Reintento con el mismo recibo: verifica contenido económico antes de reutilizar.
                    anterior = leer(destino.read_bytes())
                    if len(anterior) != 1 or any(anterior[0][k] != r[k] for k in ("cuil", "periodo", "neto", "valores")):
                        raise ValueError(f"Ya existe otro archivo para {r['empleado']}; revisar antes de reemplazar")
                else:
                    with pdfium.PdfDocument.new() as individual:
                        individual.import_pages(origen, [r["pagina"]])
                        individual.save(destino)
                relativo = f"Personal\\Recibos\\{r['anio']}\\{nombre}"
                if r["existente"]:
                    continue
                columnas = list(r["valores"])
                id_salario = execute_insert_returning_id(
                    "INSERT INTO dbo.Remuneraciones (IdContacto, [Fecha de pago], [Periodo liquidado], Recibo, "
                    + ", ".join(f"[{c}]" for c in columnas) + ") OUTPUT INSERTED.IdSalario VALUES ("
                    + ", ".join("?" for _ in range(len(columnas)+4)) + ")",
                    (r["contacto"], r["fecha"], r["periodo"], relativo, *r["valores"].values()))
                r["existente"] = id_salario
                nuevos += 1
    return {"estado": "cargado_solo" if nuevos else "ya_estaba", "total": sum(r["neto"] for r in preparados),
            "fecha": preparados[0]["fecha"], "numero": preparados[0]["periodo"], "recibos": preparados}


def procesar(mail, adj, texto: str, sha: str, id_corrida: int | None) -> str:
    from src.features.documentos_nuevos import repository, rutina

    resumen = "Resumen de Sueldos" in texto
    if resumen:
        periodo = re.search(r"Per.odo: Mensual (\d{2})/(\d{4})", texto)
        if not periodo:
            raise ValueError("No se reconoce el período del resumen de sueldos")
        mes, anio = int(periodo[1]), int(periodo[2])
        fecha = datetime(anio, mes, monthrange(anio, mes)[1])
        # El resumen usa coma de miles y punto decimal; el recibo usa formato argentino.
        filas = re.findall(r"^\d{8} .+ (\d[\d,]*\.\d{2})$", texto, re.M)
        total = re.search(r"^Total General:.* (\d[\d,]*\.\d{2})$", texto, re.M)
        if not filas or not total or sum(Decimal(v.replace(",", "")) for v in filas) != Decimal(total[1].replace(",", "")):
            raise ValueError("Los netos del resumen de sueldos no cierran al centavo")
        datos = {"fecha": fecha, "numero": f"{MESES[mes-1]} {anio}", "total": Decimal(total[1].replace(",", "")),
                 "estado": "ya_estaba"}
    else:
        recibos = leer(adj.contenido)
        datos = {"fecha": recibos[0]["fecha"]}
    carpeta = Path(remuneraciones.CARPETA_RECIBOS) / str(datos["fecha"].year)
    nombre = f"{datos['fecha']:%Y %m} {'Resumen sueldos' if resumen else 'Recibos completos'}.pdf"
    ruta = rutina._guardar(carpeta, nombre, adj.contenido, sha)
    with reconciliation_transaction():
        if not resumen:
            datos = cargar(adj.contenido, ruta)
        repository.registrar_documento({
            "idRutinaCorrida": id_corrida, "origen": "mail", "mailEntryId": mail.entry_id,
            "mailRemitente": mail.remitente, "mailAsunto": mail.asunto, "mailRecibido": mail.recibido,
            "sha256": sha, "ruta": ruta, "tipo": "resumen_sueldos" if resumen else "recibos_sueldo",
            "modulo": "tesoreria", "fecha": datos["fecha"], "numero": datos["numero"], "total": datos["total"],
            "estado": datos["estado"],
        })
    return datos["estado"]
