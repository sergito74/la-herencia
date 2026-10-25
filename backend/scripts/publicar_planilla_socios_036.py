"""Conserva el paquete Excel original y traslada SOLO celdas editadas por Artifact.

No genera fórmulas ni valores financieros: los toma del XLSX de Artifact Tool.
Preserva las otras siete hojas, vínculos externos, objetos y estilos originales.
Elimina la cadena de cálculo obsoleta y pide recálculo completo en Excel.
Por defecto prepara y verifica una copia. --publicar reemplaza el original
solo si sigue idéntico al respaldo verificado, guardando el informe de control.
"""

import argparse
import copy
import hashlib
import json
import math
import os
import re
import shutil
from lxml import etree as E  # Preserva nsmap/mc:Ignorable y extensiones nativas.
from decimal import Decimal as D
from pathlib import Path
from zipfile import ZipFile

import openpyxl  # Solo lectura de verificación; nunca save().

FOLDER = Path(__file__).resolve().parents[2] / "backups/socios-inml-5050-20261025-036"
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
E.register_namespace("r", R)


def tag(name):
    return f"{{{NS}}}{name}"


def colnum(address):
    out = 0
    for ch in re.match(r"[A-Z]+", address)[0]:
        out = out * 26 + ord(ch) - 64
    return out


def hojas(z):
    rels = {r.attrib["Id"]: r.attrib["Target"].lstrip("/") for r in E.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    return {s.attrib["name"]: (lambda p: p if p.startswith("xl/") else "xl/" + p)(rels[s.attrib[f"{{{R}}}id"]])
            for s in E.fromstring(z.read("xl/workbook.xml")).find(tag("sheets"))}


def run(publicar=False):
    info = json.loads((FOLDER / "respaldo-excel.json").read_text(encoding="utf-8"))
    backup, original = Path(info["backup"]), Path(info["original"])
    if hashlib.sha256(backup.read_bytes()).hexdigest() != info["sha256"]:
        raise ValueError("Respaldo Excel alterado")
    data = json.loads((FOLDER / "cambios-excel.json").read_text(encoding="utf-8"))
    out = FOLDER / "Cajas Giamigli-actualizado-5050.xlsx"
    patches = {}
    with ZipFile(backup) as z, ZipFile(FOLDER / "editado-artifact.xlsx") as edit:
        orig_sheets, edited_sheets = hojas(z), hojas(edit)
        shared = E.fromstring(edit.read("xl/sharedStrings.xml")) if "xl/sharedStrings.xml" in edit.namelist() else []
        styles = E.fromstring(z.read("xl/styles.xml"))
        xfs = styles.find(tag("cellXfs"))
        wrapstyles = {}
        numericstyles = {}
        numfmts = styles.find(tag("numFmts"))
        if numfmts is None:
            numfmts = E.Element(tag("numFmts"), count="0")
            styles.insert(0, numfmts)
        fmt3 = str(max([163] + [int(f.attrib["numFmtId"]) for f in numfmts]) + 1)
        E.SubElement(numfmts, tag("numFmt"), numFmtId=fmt3, formatCode="#,##0.000")
        fmt4 = str(int(fmt3) + 1)
        E.SubElement(numfmts, tag("numFmt"), numFmtId=fmt4, formatCode="#,##0.0000")
        numfmts.set("count", str(len(numfmts)))
        for p in data:
            path = orig_sheets[p["hoja"]]
            root = E.fromstring(z.read(path))
            sheetdata = root.find(tag("sheetData"))
            orig_rows = {int(r.attrib["r"]): r for r in sheetdata}
            cells = {c.attrib["r"]: c for r in sheetdata for c in r}
            authored = {c.attrib["r"]: c for r in E.fromstring(edit.read(edited_sheets[p["hoja"]])).find(tag("sheetData")) for c in r}
            changed = set(p["valores"]) | set(p["formulas"])
            for address in sorted(changed, key=lambda a: (int(re.search(r"\d+", a)[0]), colnum(a))):
                if address not in authored:
                    raise ValueError(f"Falta celda editada por Artifact {p['hoja']} {address}")
                src = copy.deepcopy(authored[address])
                if address in p["formulas"] and (src.find(tag("f")) is None or src.find(tag("v")) is None or src.attrib.get("t") == "e"):
                    raise ValueError(f"Fórmula sin resultado válido {p['hoja']} {address}")
                if src.attrib.get("t") == "s":
                    si = copy.deepcopy(shared[int(src.find(tag("v")).text)])
                    si.tag = tag("is")
                    for child in list(src):
                        src.remove(child)
                    src.attrib["t"] = "inlineStr"
                    src.append(si)
                number = int(re.search(r"\d+", address)[0])
                col = re.match(r"[A-Z]+", address)[0]
                old = cells.get(address)
                if old is not None and "s" in old.attrib:
                    style = old.attrib["s"]
                else:
                    model = "B2" if number == 2 else "A3" if col in ("A", "R", "S") else "C3" if col in ("B", "C", "D", "M", "T", "U", "V", "W") else "E3"
                    style = cells.get(model, E.Element("c")).attrib.get("s", "0")
                if number >= 3 and col in ("F", "I", "K", "G", "J", "L", "Q", "O", "P"):
                    fmt = "1" if col == "Q" else fmt3 if col in ("F", "I", "K", "P") else fmt4 if col in ("G", "J", "L") else "4"
                    key = (style, fmt)
                    if key not in numericstyles:
                        xf = copy.deepcopy(xfs[int(style)])
                        xf.set("numFmtId", fmt)
                        xf.set("applyNumberFormat", "1")
                        numericstyles[key] = str(len(xfs))
                        xfs.append(xf)
                    style = numericstyles[key]
                if col == "C" and (number > p["ultimaFila"] - p["agregados"] or address in p["valores"]):
                    if style not in wrapstyles:
                        xf = copy.deepcopy(xfs[int(style)])
                        alignment = xf.find(tag("alignment"))
                        if alignment is None:
                            alignment = E.SubElement(xf, tag("alignment"))
                        alignment.set("wrapText", "1")
                        xf.set("applyAlignment", "1")
                        wrapstyles[style] = str(len(xfs))
                        xfs.append(xf)
                    style = wrapstyles[style]
                src.set("s", style)
                row = orig_rows.get(number)
                if row is None:
                    row = E.Element(tag("row"), {"r": str(number)})
                    sheetdata.append(row)
                    orig_rows[number] = row
                if number > p["ultimaFila"] - p["agregados"]:
                    texto = str(p["valores"].get(f"C{number}", ""))
                    row.set("ht", str(max(48, math.ceil(len(texto) / 32) * 15 + 8)))
                    row.set("customHeight", "1")
                if old is not None:
                    row.remove(old)
                row.append(src)
                cells[address] = src
            for row in sheetdata:
                row[:] = sorted(row, key=lambda c: colnum(c.attrib["r"]))
            sheetdata[:] = sorted(sheetdata, key=lambda r: int(r.attrib["r"]))
            root.find(tag("dimension")).set("ref", f"A1:W{max(orig_rows)}")
            cols = root.find(tag("cols"))
            if cols is None:
                raise ValueError("La hoja de referencia carece de columnas")
            # Las columnas O:P anteriores solo tenían encabezados vacíos de uso.
            for c in list(cols):
                if int(c.attrib["min"]) >= 15:
                    cols.remove(c)
                elif int(c.attrib["max"]) >= 15:
                    c.set("max", "14")
            for n, width in ((15, 17), (16, 20), (17, 18), (18, 15), (19, 15), (20, 17), (21, 26), (22, 23), (23, 100)):
                E.SubElement(cols, tag("col"), {"min": str(n), "max": str(n), "width": str(width), "customWidth": "1"})
            patches[path] = E.tostring(root, encoding="utf-8", xml_declaration=True)
        xfs.set("count", str(len(xfs)))
        patches["xl/styles.xml"] = E.tostring(styles, encoding="utf-8", xml_declaration=True)
        # La cadena anterior contiene referencias a fórmulas ahora excluidas.
        relroot = E.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        for r in list(relroot):
            if r.attrib.get("Type", "").endswith("/calcChain"):
                relroot.remove(r)
        patches["xl/_rels/workbook.xml.rels"] = E.tostring(relroot, encoding="utf-8", xml_declaration=True)
        ct = E.fromstring(z.read("[Content_Types].xml"))
        for el in list(ct):
            if el.attrib.get("PartName") == "/xl/calcChain.xml":
                ct.remove(el)
        patches["[Content_Types].xml"] = E.tostring(ct, encoding="utf-8", xml_declaration=True)
        workbook = E.fromstring(z.read("xl/workbook.xml"))
        calc = workbook.find(tag("calcPr"))
        calc.set("fullCalcOnLoad", "1")
        calc.set("forceFullCalc", "1")
        patches["xl/workbook.xml"] = E.tostring(workbook, encoding="utf-8", xml_declaration=True)
        with ZipFile(out, "w") as dest:
            for entry in z.infolist():
                if entry.filename == "xl/calcChain.xml":
                    continue
                dest.writestr(entry, patches.get(entry.filename, z.read(entry.filename)))
    # Comprueba paquete íntegro y conservación byte a byte de todo lo ajeno.
    with ZipFile(out) as final, ZipFile(backup) as before:
        if final.testzip() is not None:
            raise ValueError("Archivo Excel corrupto")
        for name in before.namelist():
            if name not in patches and name != "xl/calcChain.xml" and final.read(name) != before.read(name):
                raise ValueError(f"Cambio ajeno al alcance {name}")
    values = openpyxl.load_workbook(out, data_only=True)
    formulas = openpyxl.load_workbook(out, data_only=False)
    system = json.loads((FOLDER / "sistema.json").read_text(encoding="utf-8"))
    regs = {r["IdMovimiento"]: r for r in system["movimientos"] if not r["Anulada"]}
    informe = {"estado": "copia_verificada", "original": str(original), "backup": str(backup), "copia": str(out), "socios": []}
    for p in data:
        s, f = values[p["hoja"]], formulas[p["hoja"]]
        ids = []
        kg, usd, nominal, mutuo = D(0), D(0), D(0), D(0)
        for e in p["enlaces"]:
            row, r = e["fila"], regs[e["id"]]
            ids.append(r["IdMovimiento"])
            colimp, colkg, colusd, sign = ("E", "F", "G", -1) if r["Tipo"] == "AsignacionGasto" else ("H", "I", "J", 1)
            for col, expected, tol in ((colimp, r["Importe"], ".00001"), (colkg, r["ImporteKgCarne"], ".00001"), (colusd, r["ImporteUSD"], ".00001")):
                if abs(D(str(s[f"{col}{row}"].value)) - D(expected)) > D(tol):
                    raise ValueError(f"Diferencia contra WC {p['hoja']} {col}{row} (asiento {e['id']})")
            nominal += sign * D(r["Importe"])
            if r["Origen"] == "Mutuo2018":
                mutuo += sign * D(r["ImporteUSD"])
            else:
                kg += sign * D(r["ImporteKgCarne"])
                usd += sign * D(r["ImporteUSD"])
        if len(ids) != len(set(ids)):
            raise ValueError("Asiento duplicado")
        socio = regs[ids[0]]["IdSocio"]
        if set(ids) != {id_ for id_, r in regs.items() if r["IdSocio"] == socio}:
            raise ValueError("La planilla no contiene exactamente todos los asientos activos")
        last = p["ultimaFila"]
        for address, expected, tolerance in ((f"K{last}", kg, ".00001"), (f"L{last}", usd, ".00001"), (f"N{last}", nominal, ".00001"),
                                             ("C1", kg * D(str(s["W10"].value)) + usd * D(str(s["W9"].value)), ".01")):
            if abs(D(str(s[address].value)) - expected) > D(tolerance):
                raise ValueError(f"Saldo diferente {p['hoja']} {address}")
        for address, expected in p["formulas"].items():
            if f[address].value != expected:
                raise ValueError(f"Fórmula no preservada {p['hoja']} {address}")
        if socio == 2 and D(str(s["W1"].value)) != mutuo:
            raise ValueError("Mutuo diferente")
        informe["socios"].append({"hoja": p["hoja"], "asientos": len(ids), "agregados": p["agregados"], "kgAFavor": kg,
                                  "usdAFavor": usd, "nominalAFavor": nominal, "actualizadaAFavor": s["C1"].value, "mutuoUSD": mutuo})
    values.close()
    formulas.close()
    if publicar:
        if hashlib.sha256(original.read_bytes()).hexdigest() != info["sha256"]:
            raise ValueError("Cambió el original desde el respaldo; no se reemplaza")
        staging = original.with_name(original.stem + ".sincronizacion.tmp")
        shutil.copyfile(out, staging)
        if hashlib.sha256(staging.read_bytes()).hexdigest() != hashlib.sha256(out.read_bytes()).hexdigest():
            raise ValueError("Copia temporal incorrecta")
        os.replace(staging, original)
        informe["estado"] = "original_actualizado"
        informe["sha256Final"] = hashlib.sha256(original.read_bytes()).hexdigest()
    (FOLDER / "verificacion-excel.json").write_text(json.dumps(informe, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(informe, default=str, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--publicar", action="store_true")
    run(p.parse_args().publicar)
