"""Actualiza el catálogo de insumos con los padrones públicos vigentes, 2026-10-15.

El catálogo (`vw_ProductosBase`) es una copia vieja heredada del Access:
fitosanitarios hasta el registro SENASA 41629 y solo 890 cultivares de INASE.
Este script agrega lo que falta, sin tocar lo existente:

1. **Fitosanitarios** (dbo.Formulados), desde el Registro Nacional de
   Terapéutica Vegetal de SENASA (API pública del vademécum). El Id es el N°
   de registro. Los biológicos ("42811 BIO") usan el número sin el sufijo,
   salvo que choque con otro producto. La API pública no informa la aptitud;
   se deduce del principio activo, por voto de los productos ya cargados con
   el mismo activo, y si no hay ninguno queda "SD - Sin clasificar".
2. **Semillas** (dbo.Semillas), desde el Catálogo Nacional de Cultivares de
   INASE. El Id es 100.000.000 + N° de registro INASE (convención heredada).
   Tipo 3 = inscripto también en RNPC, 1 = solo RNC.

Fertilizantes queda afuera: SENASA ahora numera "ST-F-100040", que no
corresponde con los números heredados de dbo.Fertilizantes.

Es idempotente (inserta solo los Ids que no están en la vista) y hace un
respaldo verificado antes de grabar.

Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.actualizar_catalogo_senasa_inase [--aplicar]
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import date

from src.db.connection import execute_write_transaction, fetch_all

SENASA = ("https://aps2.senasa.gov.ar/adt_api/api/productosAgroquimicosFormulados/search/"
          "publicSearchProductosFormuladosDTO?page={}&size=2000&sort=numeroInscripcion,desc")
INASE = ("https://gestion.inase.gob.ar/registroCultivares/publico/catalogo/servicio?draw=1&start={}&length=100"
         "&columns%5B1%5D%5Bdata%5D=numero_registro&order%5B0%5D%5Bcolumn%5D=1&order%5B0%5D%5Bdir%5D=asc")
OFFSET_SEMILLAS = 100_000_000
SIN_CLASIFICAR = "SD"
# Biológicos sin antecedente en el catálogo: aptitud por el organismo.
APTITUD_BIO = [("BEAUVERIA", "IN"), ("METARHIZIUM", "IN"), ("THURINGIENSIS", "IN"), ("BACULOVIRUS", "IN"),
               ("TRICHODERMA", "FU"), ("BACILLUS", "FU"), ("STREPTOMYCES", "FU"), ("PSEUDOMONAS", "FU")]


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def descargar_senasa() -> list[dict]:
    out, page = [], 0
    while True:
        d = _get_json(SENASA.format(page))
        out += d["_embedded"]["productosAgroquimicosFormulados"]
        page += 1
        if page >= d["page"]["totalPages"]:
            return out


def descargar_inase() -> list[dict]:
    out, start = [], 0
    while True:  # el servicio devuelve vacío si se piden más de 100 por página
        d = _get_json(INASE.format(start))
        out += d["aaData"]
        start += 100
        if not d["aaData"] or start >= d["iTotalDisplayRecords"]:
            return out


def _activos(texto: str) -> list[tuple[str, str]]:
    """'FLUMIOXAZIN <b>4,8%</b>, IMAZETAPIR <b>7%</b>' -> [('FLUMIOXAZIN', '4,8'), ('IMAZETAPIR', '7')]."""
    return [(n.strip(" ,").upper(), c.replace("%", "").strip())
            for n, c in re.findall(r"([^<]+?)\s*<b>([^<]*)</b>", texto or "")]


def _votos_aptitud() -> dict[str, Counter]:
    votos: dict[str, Counter] = defaultdict(Counter)
    for r in fetch_all("SELECT [INGREDIENTE ACTIVO] AS ia, APTITUDES AS ap FROM dbo.Formulados WHERE APTITUDES IS NOT NULL"):
        for ia in re.split(r"\s*\+\s*", (r["ia"] or "").upper()):
            if ia.strip():
                votos[ia.strip()][r["ap"]] += 1
    return votos


def _aptitud(activos: list[tuple[str, str]], votos: dict[str, Counter]) -> str:
    total = Counter()
    for nombre, _ in activos:
        total.update(votos.get(nombre, Counter()))
    if total:
        return total.most_common(1)[0][0]
    texto = " ".join(n for n, _ in activos)
    return next((ap for clave, ap in APTITUD_BIO if clave in texto), SIN_CLASIFICAR)


def _fecha(s: str | None):
    return date.fromisoformat(s) if s else None


def main(aplicar: bool) -> None:
    ids = {int(r["id"]) for r in fetch_all("SELECT CAST(IdProducto AS bigint) AS id FROM dbo.vw_ProductosBase")}
    stmts: list = []

    if not fetch_all("SELECT 1 AS x FROM dbo.[Tipo formulado] WHERE IdTipo = ?", (SIN_CLASIFICAR,)):
        stmts.append(("INSERT INTO dbo.[Tipo formulado] (IdTipo, Tipo) VALUES (?, ?)", (SIN_CLASIFICAR, "Sin clasificar")))

    votos = _votos_aptitud()
    nuevos_f, choques, aptitudes = [], [], Counter()
    for p in sorted(descargar_senasa(), key=lambda x: x["numeroInscripcion"]):
        m = re.fullmatch(r"(\d+)(?:\s*BIO)?", p["numeroInscripcion"].strip())
        if not m:
            choques.append(p["numeroInscripcion"])
            continue
        nro = int(m.group(1))
        if nro in ids:
            if not p["numeroInscripcion"].strip().isdigit():
                choques.append(p["numeroInscripcion"])
            continue
        ids.add(nro)
        activos = _activos(p["sustanciasActivas"])
        ap = _aptitud(activos, votos)
        aptitudes[ap] += 1
        nuevos_f.append((p["marca"].strip(), nro, ap))
        stmts.append((
            "INSERT INTO dbo.Formulados (APTITUDES, EMPRESA, [Nº REG], [MARCA COMERCIAL], [INGREDIENTE ACTIVO],"
            " CT, CONCENTRACION, NroReg_int) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ap, p["nombreFirma"], float(nro), p["marca"].strip(), " + ".join(n for n, _ in activos) or None,
             p["claseToxicologica"], " + ".join(c for _, c in activos) or None, nro)))

    nuevos_s = []
    hoy = date.today()
    for c in descargar_inase():
        nro = OFFSET_SEMILLAS + int(c["numero_registro"])
        if nro in ids:
            continue
        ids.add(nro)
        validez = _fecha(c["validez_rnpc"])
        nuevos_s.append((c["nombre_definitivo"], c["especie"]))
        stmts.append((
            "INSERT INTO dbo.Semillas ([Nro Registro], Especie, [Condicion Genetica], [Nombre Botanico], Cultivar, Tipo,"
            " Caracteristica, [G Especie], [Inscripcion RNC], [Inscripcion RNPC], [Validez RNPC], Vigencia, Pais,"
            " Solicitante, Representante, [Evento de Transformacion]) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (nro, c["especie"], c["condicion_genetica"], c["nombre_cientifico"], c["nombre_definitivo"],
             3.0 if c["inscripcion_rnpc"] else 1.0, c["caracteristicas"] or None, c["grupo_especie"],
             _fecha(c["inscripcion_rnc"]), _fecha(c["inscripcion_rnpc"]), validez,
             "S" if validez and validez >= hoy else None, c["cod_pais"],
             c["solicitante_rnc"] or c["solicitante_rnpc"] or None, c["representante_rnc"] or c["representante_rnpc"] or None,
             c["evento_transgenico"])))

    print(f"Fitosanitarios nuevos: {len(nuevos_f)}  aptitudes: {dict(aptitudes.most_common())}")
    print(f"  no cargados (número ya usado o sin formato): {len(choques)} {choques[:10]}")
    print(f"Cultivares nuevos: {len(nuevos_s)}  especies: {dict(Counter(e for _, e in nuevos_s).most_common(8))}")
    for marca, nro, ap in nuevos_f:
        if "EBC" in marca.upper() and "FLUMI" in marca.upper():
            print(f"  ej.: {nro} {marca} [{ap}]")

    if not aplicar:
        print("\nSimulación: no se grabó nada. Correr con --aplicar.")
        return
    from src.features.vinculos.backup import backup_verificado
    print(f"Respaldo verificado: {backup_verificado('catalogo-senasa-inase')}")
    execute_write_transaction(stmts)
    print(f"Grabado: {len(stmts)} filas.")


if __name__ == "__main__":
    main("--aplicar" in sys.argv)
