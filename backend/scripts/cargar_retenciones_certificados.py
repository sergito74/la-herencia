"""Completa dbo.Retenciones con los certificados SICORE emitidos (2026-10-01).

Fuente: los PDF de "Documents/La Herencia/Administracion y gestion/
Cuentas a pagar/Certificados Retenciones/<año>/". Cada PDF trae número,
fecha, CUIT del retenido, factura que origina la retención e importe.

- **Coincidencia**: una retención ya está cargada si la tabla tiene una fila
  con el mismo importe (±0,01) y una fecha a 5 días o menos. La numeración
  de la tabla no es confiable: hay números corridos en uno y sufijos " B".
- **Contacto**: se busca por el CUIT de Contactos. Si no está cargado, se usa
  el contacto que ya tienen las retenciones anteriores del mismo CUIT.
- **Número repetido**: el software de SICORE volvió a numerar desde 1 en
  julio de 2026. Si el número ya existe en la tabla con otra fecha, se le
  agrega " B", que es la convención que ya usa la tabla (ej. "0000-2024-000030 B").
- **Escaneados**: los PDF que son imágenes van en `ESCANEADOS`, transcriptos
  a mano.
- **Filas existentes**: una fila con el mismo número e importe pero la fecha
  mal cargada se corrige. Una fila con el mismo número e importe 0 se
  completa con los datos del certificado.
- **Correcciones manuales**: van en `CORRECCIONES`, cada una con su motivo.

Es idempotente: una segunda corrida no inserta nada. Antes de escribir hace
un respaldo verificado de WC.

Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.cargar_retenciones_certificados [--aplicar]
"""

from __future__ import annotations

import glob
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import pdfplumber

from src.db.connection import execute_write_transaction, fetch_all

CARPETA = Path(r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Cuentas a pagar\Certificados Retenciones")
CUIT_AGENTE = "30712114602"

# PDF escaneados de 2026 (imágenes), transcriptos el 2026-10-01 y verificados
# contra "Detalle de Pagos.xlsx".
ESCANEADOS = [
    {"numero": "0000-2026-000006", "fecha": "21/07/2026", "cuit": "20413155089", "importe": 45456.60,
     "comprobante": "00001-00000055", "archivo": "0000-2026-000006_SantosAgustin (bis).pdf"},
    {"numero": "0000-2026-000007", "fecha": "06/08/2026", "cuit": "30708885084", "importe": 24725.38,
     "comprobante": "00002-00000060", "archivo": "0000-2026-000007_FideicomisoLaEsperanza (bis).pdf"},
]

# Certificados que NO se completan aunque la fila de la tabla esté en 0: la retención nunca se descontó en plata.
OMITIDOS = {
    "0000-2021-000001": "Syngenta: certificado con base de $603.180,90 que no es la de la ND 0274-2567 ($8.723,40); el pago del 18/01/2021 "
                        "fue el total sin descontar retención. Sergio la dejó en $0 a propósito (2026-10-08).",
}

# (IdRetencionSQL, columna, valor esperado antes, valor nuevo, motivo)
CORRECCIONES = [
    (None, "IdContacto", 458, 562, "Certificado 0000-2024-000030 B: el retenido es Fideicomiso La Esperanza "
                                   "(CUIT 30-70888508-4), dueño de la factura 00002-00000013."),
]


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def leer_pdfs() -> list[dict]:
    certs = []
    for f in sorted(glob.glob(str(CARPETA / "*" / "*.pdf"))):
        with pdfplumber.open(f) as p:
            t = "\n".join(pg.extract_text() or "" for pg in p.pages)
        numero = re.search(r"Certificado N.{0,3}:\s*([0-9]{4}-[0-9]{4}-[0-9]{6})", t)
        fecha = re.search(r"Fecha\s*:\s*(\d{2}/\d{2}/\d{4})", t)
        monto = re.search(r"Monto de la Retenci.n\s*:\s*\$\s*([\d\.,]+)", t)
        if not (numero and fecha and monto):
            continue  # escaneado: va en ESCANEADOS si hace falta
        cuits = [re.sub(r"\D", "", c) for c in re.findall(r"(\d{2}-\d{8}-\d)", t)]
        comp = re.search(r"Tique Nro\.?\s*\n?\s*([0-9]{4,5}-[0-9]{8})", t)
        certs.append({"numero": numero.group(1), "fecha": fecha.group(1),
                      "cuit": next((c for c in cuits if c != CUIT_AGENTE), ""), "importe": round(_num(monto.group(1)), 2),
                      "comprobante": comp.group(1) if comp else "", "archivo": Path(f).name})
    return certs + ESCANEADOS


def main(aplicar: bool) -> None:
    tabla = fetch_all("SELECT IdRetencionSQL AS id, [Numero Certificado] AS n, Fecha AS f, IdContacto AS c, "
                      "Importe AS i FROM dbo.Retenciones")
    contactos_cuit = {re.sub(r"\D", "", str(x["cuit"])): x["id"] for x in fetch_all(
        "SELECT IdContacto AS id, [CUIT/CUIL] AS cuit FROM dbo.Contactos WHERE [CUIT/CUIL] IS NOT NULL")}

    certs = leer_pdfs()
    for c in certs:
        c["f"] = datetime.strptime(c["fecha"], "%d/%m/%Y")

    def coincide(c, t):
        return t["f"] and abs((t["f"] - c["f"]).days) <= 5 and abs(float(t["i"] or 0) - c["importe"]) <= 0.01

    # Contacto por CUIT aprendido de las retenciones ya cargadas.
    aprendido: dict[str, Counter] = defaultdict(Counter)
    for c in certs:
        for t in tabla:
            if coincide(c, t) and t["c"]:
                aprendido[c["cuit"]][t["c"]] += 1

    usadas: set[int] = set()
    nuevas, sin_contacto, completar = [], [], []
    numeros = {t["n"].strip() for t in tabla}
    for c in sorted(certs, key=lambda c: c["f"]):
        if c["numero"] in OMITIDOS:
            continue
        t = next((t for t in tabla if t["id"] not in usadas and coincide(c, t)), None)
        if t:
            usadas.add(t["id"])
            continue
        mismo_numero = [t for t in tabla if t["id"] not in usadas and t["n"].strip() == c["numero"]]
        # Mismo número e importe con otra fecha: la fila está, con la fecha mal cargada.
        t = next((t for t in mismo_numero if abs(float(t["i"] or 0) - c["importe"]) <= 0.01), None)
        if t:
            usadas.add(t["id"])
            if abs((t["f"] - c["f"]).days) > 31:
                completar.append((t, {"Fecha": c["f"]}, f"{c['numero']}: fecha {t['f']:%d/%m/%Y} pasa a {c['fecha']}"))
            continue
        # Mismo número con importe 0: la fila está vacía y se completa.
        t = next((t for t in mismo_numero if not float(t["i"] or 0)), None)
        contacto = contactos_cuit.get(c["cuit"]) or (aprendido[c["cuit"]].most_common(1)[0][0]
                                                     if aprendido.get(c["cuit"]) else None)
        if contacto is None:
            sin_contacto.append(c)
            continue
        if t:
            usadas.add(t["id"])
            completar.append((t, {"Fecha": c["f"], "IdContacto": t["c"] or contacto, "Importe": c["importe"]},
                              f"{c['numero']}: fila vacía completada con ${c['importe']:,.2f} del {c['fecha']}"))
            continue
        numero = c["numero"] if c["numero"] not in numeros else f"{c['numero']} B"
        numeros.add(numero)
        nuevas.append((numero, c["f"], contacto, c["importe"], c))

    print(f"Certificados leídos: {len(certs)}. Ya cargados: {len(usadas)}. A agregar: {len(nuevas)}.")
    for numero, f, contacto, importe, c in nuevas:
        print(f"  + {numero:20} {f:%d/%m/%Y} contacto {contacto:4} ${importe:>14,.2f}  factura {c['comprobante']}  ({c['archivo']})")
    for _, _, motivo in completar:
        print(f"  ~ {motivo}")
    for c in sin_contacto:
        print(f"  ? sin contacto: {c['numero']} {c['fecha']} CUIT {c['cuit']} ${c['importe']:,.2f} ({c['archivo']})")

    stmts = [("INSERT INTO dbo.Retenciones ([Numero Certificado], Fecha, IdContacto, Importe) VALUES (?, ?, ?, ?)",
              (numero, f, contacto, importe)) for numero, f, contacto, importe, _ in nuevas]
    for t, cambios, _ in completar:
        stmts.append((f"UPDATE dbo.Retenciones SET {', '.join(f'{k} = ?' for k in cambios)} WHERE IdRetencionSQL = ?",
                      (*cambios.values(), t["id"])))
    for id_ret, columna, antes, nuevo, motivo in CORRECCIONES:
        if id_ret is None:  # 0000-2024-000030 B
            fila = next((t for t in tabla if t["n"].strip() == "0000-2024-000030 B"), None)
            id_ret = fila["id"] if fila else None
        fila = next((t for t in tabla if t["id"] == id_ret), None)
        actual = None if fila is None else (fila["i"] if columna == "Importe" else fila["c"])
        if fila is None or actual is None or abs(float(actual) - float(antes)) > 0.01:
            print(f"  = corrección ya hecha o no aplicable: {motivo}")
            continue
        print(f"  ~ {motivo}")
        stmts.append((f"UPDATE dbo.Retenciones SET {columna} = ? WHERE IdRetencionSQL = ?", (nuevo, id_ret)))

    if not aplicar:
        print("Simulación: no se escribió nada. Usar --aplicar para grabar.")
        return
    if not stmts:
        print("Nada para grabar.")
        return
    from src.features.vinculos.backup import backup_verificado
    print(f"Respaldo verificado: {backup_verificado('retenciones-certificados')}")
    execute_write_transaction(stmts)
    print(f"Grabado: {len(nuevas)} retenciones nuevas y {len(stmts) - len(nuevas)} correcciones.")


if __name__ == "__main__":
    main(aplicar="--aplicar" in sys.argv)
