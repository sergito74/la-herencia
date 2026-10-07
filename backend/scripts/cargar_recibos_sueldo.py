"""Carga en dbo.Remuneraciones los recibos de sueldo en PDF que faltan (2026-10-01).

Fuente: `Documents/La Herencia/Administracion y gestion/Personal/Recibos/<año>/`,
con un PDF por empleado y mes. Los anteriores a 2016 ya están cargados sin
PDF de respaldo.

Cada concepto del recibo (código de 4 dígitos) va a una columna de la tabla
según `CONCEPTOS`. **Control**: la suma de haberes menos deducciones tiene
que dar el NETO del PDF, con una tolerancia de $1. Si no da, el recibo no se
carga y se informa.

No duplica: saltea el recibo si ya existe uno del mismo contacto y período
("Enero 2026"). Antes de grabar hace un respaldo verificado de WC.

Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.cargar_recibos_sueldo [--desde 2025-12] [--corregir] [--aplicar]
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pdfplumber

from src.db.connection import execute_write_transaction, fetch_all

CARPETA = Path(r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Personal\Recibos")

EMPLEADOS = {  # nombre en el archivo (sin espacios, minúsculas) → IdContacto
    "armandomori": 376, "irmamiranda": 46, "marcelosierra": 374, "sergiogiamberardini": 375, "diegopardo": 632, "pardodiego": 632,
    "albertogorosito": 519, "francorodriguez": 379,
}

HABERES = ["Sueldo basico", "Adic futuros aumentos", "Ajuste", "Vacaciones", "Dia Gremio", "Antiguedad",
           "Ajuste No Remunerativo", "Aguinaldo", "Redondeo", "Bonificacion adicional"]
DEDUCCIONES = ["Jubilacion", "Ley 19032", "Obra Social", "Obra Social Acuerdos", "Aporte Sindical", "Servicio de Sepelio"]

CONCEPTOS = {
    "0004": "Sueldo basico", "0010": "Sueldo basico", "0012": "Sueldo basico", "0017": "Sueldo basico",
    "0200": "Antiguedad", "0154": "Antiguedad",
    "0024": "Ajuste", "0084": "Ajuste", "0274:RETROACT AJUSTE": "Ajuste",
    "0166": "Ajuste No Remunerativo", "0274:RETROACT ASIG NO REM": "Ajuste No Remunerativo",
    "0401": "Ajuste No Remunerativo",
    "0071": "Vacaciones", "0199": "Vacaciones", "0204": "Vacaciones",
    "0203": "Aguinaldo", "0298": "Aguinaldo",
    "0300": "Jubilacion", "0302": "Ley 19032", "0310": "Obra Social", "0315": "Obra Social Acuerdos",
    "0322": "Aporte Sindical", "0324": "Servicio de Sepelio",
    "0800": "Redondeo",
    "0077": "Bonificacion adicional",
}

# Recibos escaneados (formato ARCA casas particulares, empleadora Albina
# Iglina), transcriptos el 2026-10-01. Columnas y neto del PDF.
ESCANEADOS = {
    "2026 06 Irma Miranda.pdf": {"mes": 6, "anio": 2026, "fechaPago": "30/06/2026", "neto": 337022.00,
                                 "valores": {"Sueldo basico": 216039.83, "Antiguedad": 8641.58, "Aguinaldo": 112340.59}},
    "2026 07 Irma Miranda.pdf": {"mes": 7, "anio": 2026, "fechaPago": "28/07/2026", "neto": 224682.00,
                                 "valores": {"Sueldo basico": 216040.42, "Antiguedad": 8641.58}},
    "2026 08 Irma Miranda.pdf": {"mes": 8, "anio": 2026, "fechaPago": "07/09/2026", "neto": 248911.00,
                                 "valores": {"Sueldo basico": 228279.82, "Antiguedad": 9131.18,
                                             "Ajuste No Remunerativo": 11500.00}},
    "2026 09 Irma Miranda.pdf": {"mes": 9, "anio": 2026, "fechaPago": "14/09/2026", "neto": 244274.00,
                                 "valores": {"Sueldo basico": 234878.86, "Antiguedad": 9395.14}},
}

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
         "Noviembre", "Diciembre"]


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def leer_recibo(pdf: Path) -> dict:
    with pdfplumber.open(pdf) as p:
        t = p.pages[0].extract_text()
    # Dos formatos: el del sistema anterior (hasta mayo de 2026, recibo
    # duplicado) y el nuevo (desde junio de 2026, deducciones en negativo y
    # sin fecha de pago: se usa el último día del mes, que coincide con la
    # transferencia del neto).
    periodo = re.search(r"Per.odo: Mensual (\d{2})/(\d{4})", t) or re.search(r"^Mensual (\d{2}) (\d{4})", t, re.M)
    pago = re.search(r"Fecha de Pago: \w+, (\d{2}/\d{2}/\d{4})", t)
    neto = re.search(r"^NETO ([\d\.]+,\d{2})", t, re.M) or re.search(r"SUELDO NETO \$ ([\d\.]+,\d{2})", t)
    valores = {c: 0.0 for c in HABERES + DEDUCCIONES}
    desconocidos = []
    for linea in t.splitlines():
        m = re.match(r"^(\d{4}) (.+)$", linea)
        if not m:
            continue
        codigo, resto = m.group(1), m.group(2)
        mitad = resto.split(f" {codigo} ")[0]  # el recibo viene duplicado (original y copia)
        nombre = re.sub(r"[\d\.,\s\-]+$", "", mitad).strip()
        numeros = re.findall(r"-?\d[\d\.]*,\d{2}", mitad[len(nombre):])
        if not numeros:
            continue
        columna = CONCEPTOS.get(f"{codigo}:{nombre}") or CONCEPTOS.get(codigo)
        if codigo == "0274":  # retroactivo: el nombre puede traer el mes ("RETROACT AJUSTE 07/")
            columna = "Ajuste No Remunerativo" if "ASIG" in nombre else "Ajuste"
        if columna is None:
            desconocidos.append(f"{codigo} {nombre}")
            continue
        valores[columna] += abs(_num(numeros[-1]))
    if periodo is None or neto is None:
        return None  # PDF escaneado (imagen): va en ESCANEADOS
    mes, anio = int(periodo.group(1)), int(periodo.group(2))
    if pago:
        fecha_pago = datetime.strptime(pago.group(1), "%d/%m/%Y")
    else:
        fecha_pago = (datetime(anio + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1))
    calculado = sum(valores[c] for c in HABERES) - sum(valores[c] for c in DEDUCCIONES)
    return {"periodo": f"{MESES[mes - 1]} {anio}", "mesAnio": (mes, anio), "fechaPago": fecha_pago,
            "neto": _num(neto.group(1)), "calculado": round(calculado, 2), "valores": valores,
            "desconocidos": desconocidos}


def _mes_anio(p: str) -> tuple[int, int] | None:
    p = p.strip()
    m1 = re.match(r"(\w+) (\d{4})$", p)
    m2 = re.match(r"\d{2}/(\d{2})/(\d{4})$", p)
    if m1 and m1.group(1).capitalize() in MESES:
        return MESES.index(m1.group(1).capitalize()) + 1, int(m1.group(2))
    if m2:
        return int(m2.group(1)), int(m2.group(2))
    return None


def corregir(aplicar: bool, desde: str) -> None:
    """Corrige recibos ya cargados cuyo neto no coincide con el PDF (2026-10-01:
    los de Sierra de 2023-2025 estaban cargados en bruto, sin deducciones).
    Solo toca meses con una única fila cargada; los duplicados se informan."""
    columnas = HABERES + DEDUCCIONES
    sel = ", ".join(f"ISNULL([{c}], 0) AS [{c}]" for c in columnas)
    filas = fetch_all(f"SELECT IdSalario, IdContacto, [Periodo liquidado] AS p, {sel} FROM dbo.Remuneraciones "
                      "WHERE [Periodo liquidado] IS NOT NULL")
    indice: dict[tuple, list] = {}
    for f in filas:
        k = _mes_anio(f["p"])
        if k:
            indice.setdefault((f["IdContacto"], *k), []).append(f)
    cambios, avisos = [], []
    for pdf in sorted(CARPETA.glob("*/*.pdf")):
        m = re.match(r"(\d{4}) (\d{2})[_ ](.+)\.pdf$", pdf.name)
        if not m or f"{m.group(1)}-{m.group(2)}" < desde:
            continue
        contacto = EMPLEADOS.get(re.sub(r"\s+", "", m.group(3)).lower())
        r = leer_recibo(pdf) if contacto else None
        if r is None or r["desconocidos"] or abs(r["calculado"] - r["neto"]) > 1:
            continue
        cargadas = indice.get((contacto, *r["mesAnio"]), [])
        if len(cargadas) != 1:
            if len(cargadas) > 1:
                avisos.append(f"{pdf.name}: {len(cargadas)} filas cargadas para el mismo mes (no se toca)")
            continue
        fila = cargadas[0]
        neto_base = sum(float(fila[c]) for c in HABERES) - sum(float(fila[c]) for c in DEDUCCIONES)
        if abs(neto_base - r["neto"]) <= 1:
            continue
        # Prueba independiente: el neto del PDF tiene que ser una transferencia
        # al empleado dentro de los 45 días posteriores al fin del período.
        mes, anio = r["mesAnio"]
        fin = datetime(anio + (mes == 12), mes % 12 + 1, 1)
        pagos = fetch_all("SELECT Credito AS c FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ? AND Credito > 0 "
                          "AND Origen <> 'Remuneraciones' AND Fecha BETWEEN ? AND ?",
                          (contacto, fin - timedelta(days=15), fin + timedelta(days=45)))
        if not any(abs(float(p["c"]) - r["neto"]) <= 1 for p in pagos):
            avisos.append(f"{pdf.name}: neto PDF {r['neto']:,.2f} sin transferencia que lo confirme (no se toca)")
            continue
        cambios.append((fila["IdSalario"], r, neto_base, pdf.name))
    print(f"Recibos a corregir: {len(cambios)}")
    for id_sal, r, neto_base, nombre in cambios:
        print(f"  {nombre:36} cargado {neto_base:>13,.2f}  PDF {r['neto']:>13,.2f}")
    for a in avisos:
        print(f"  ? {a}")
    if not aplicar or not cambios:
        return
    from src.features.vinculos.backup import backup_verificado
    print(f"Respaldo verificado: {backup_verificado('recibos-sueldo-correccion')}")
    execute_write_transaction([
        ("UPDATE dbo.Remuneraciones SET " + ", ".join(f"[{c}] = ?" for c in columnas) + " WHERE IdSalario = ?",
         (*[round(r["valores"][c], 2) or None for c in columnas], id_sal)) for id_sal, r, _, _ in cambios])
    print(f"Corregidos {len(cambios)} recibos.")


def main(aplicar: bool, desde: str) -> None:
    # El período está cargado como "Noviembre 2025" o como "30/11/2025"
    # (Marcelo Sierra): se compara por (contacto, mes, año).
    existentes = set()
    for f in fetch_all("SELECT IdContacto AS c, [Periodo liquidado] AS p FROM dbo.Remuneraciones "
                       "WHERE [Periodo liquidado] IS NOT NULL"):
        p = f["p"].strip()
        m1 = re.match(r"(\w+) (\d{4})$", p)
        m2 = re.match(r"\d{2}/(\d{2})/(\d{4})$", p)
        if m1 and m1.group(1).capitalize() in MESES:
            existentes.add((f["c"], MESES.index(m1.group(1).capitalize()) + 1, int(m1.group(2))))
        elif m2:
            existentes.add((f["c"], int(m2.group(1)), int(m2.group(2))))
    nuevos, problemas = [], []
    for pdf in sorted(CARPETA.glob("*/*.pdf")):
        m = re.match(r"(\d{4}) (\d{2})[_ ](.+)\.pdf$", pdf.name)
        if not m or f"{m.group(1)}-{m.group(2)}" < desde:
            continue
        clave = re.sub(r"\s+", "", m.group(3)).lower()
        contacto = EMPLEADOS.get(clave)
        if contacto is None:
            problemas.append(f"{pdf.name}: empleado desconocido")
            continue
        r = leer_recibo(pdf)
        if r is None and pdf.name in ESCANEADOS:
            e = ESCANEADOS[pdf.name]
            valores = {c: 0.0 for c in HABERES + DEDUCCIONES} | e["valores"]
            calculado = round(sum(valores[c] for c in HABERES) - sum(valores[c] for c in DEDUCCIONES), 2)
            r = {"periodo": f"{MESES[e['mes'] - 1]} {e['anio']}", "mesAnio": (e["mes"], e["anio"]),
                 "fechaPago": datetime.strptime(e["fechaPago"], "%d/%m/%Y"), "neto": e["neto"],
                 "calculado": calculado, "valores": valores, "desconocidos": []}
        if r is None:
            problemas.append(f"{pdf.name}: es una imagen, sin texto para leer")
            continue
        if (contacto, *r["mesAnio"]) in existentes:
            continue
        if r["desconocidos"] or abs(r["calculado"] - r["neto"]) > 1:
            problemas.append(f"{pdf.name}: neto {r['neto']:,.2f} calculado {r['calculado']:,.2f} "
                             f"conceptos sin mapear {r['desconocidos']}")
            continue
        r.update(contacto=contacto, pdf=pdf)
        nuevos.append(r)

    print(f"Recibos a cargar: {len(nuevos)}")
    for r in nuevos:
        print(f"  {r['periodo']:16} contacto {r['contacto']:4} pago {r['fechaPago']:%d/%m/%Y} neto ${r['neto']:>13,.2f}  {r['pdf'].name}")
    for p in problemas:
        print(f"  ? {p}")
    if not aplicar:
        print("Simulación: no se escribió nada. Usar --aplicar para grabar.")
        return
    if not nuevos:
        return
    from src.features.vinculos.backup import backup_verificado
    print(f"Respaldo verificado: {backup_verificado('recibos-sueldo')}")
    columnas = HABERES + DEDUCCIONES
    stmts = []
    for r in nuevos:
        ruta = "..\\..\\..\\" + str(r["pdf"]).split("Sergio\\", 1)[1]
        stmts.append((
            "INSERT INTO dbo.Remuneraciones (IdContacto, [Fecha de pago], [Periodo liquidado], "
            + ", ".join(f"[{c}]" for c in columnas) + ", Recibo) VALUES (?, ?, ?, " + ", ".join("?" * len(columnas)) + ", ?)",
            (r["contacto"], r["fechaPago"], r["periodo"], *[round(r["valores"][c], 2) or None for c in columnas],
             f"{ruta}#{ruta}#")))
    execute_write_transaction(stmts)
    print(f"Grabados {len(nuevos)} recibos.")


if __name__ == "__main__":
    args = sys.argv[1:]
    desde = args[args.index("--desde") + 1] if "--desde" in args else "2025-12"
    if "--corregir" in args:
        corregir(aplicar="--aplicar" in args, desde=desde)
    else:
        main(aplicar="--aplicar" in args, desde=desde)
