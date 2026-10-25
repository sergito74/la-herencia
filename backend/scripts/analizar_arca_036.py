"""Análisis reproducible, sin escrituras SQL, de la instantánea ARCA 25/10.

WC se exportó en backups/arca-analisis-20261025/wc.json; las fuentes de
correo y los certificados se conservan allí. Los emparejamientos por suma
son propuestas verificables, nunca aplicaciones automáticas ni saldo fiscal.
"""
import itertools
import json
import re
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "backups/arca-analisis-20261025"


def cargar(name, bom=False):
    return json.loads((ROOT / name).read_text(encoding="utf-8-sig" if bom else "utf-8"))


def dinero(value):
    return D(str(value or 0))


def monto_es(value):
    return D(value.replace(".", "").replace(",", "."))


def run():
    wc = cargar("wc.json")
    certificados = cargar("retenciones-fechadas.json")
    avisos = cargar("avisos-cargas-sociales.json", bom=True)
    por_origen, por_anio = {}, defaultdict(lambda: D(0))
    for r in wc["movimientos"]:
        g = por_origen.setdefault(r["Origen"], {"cantidad": 0, "deuda": D(0), "credito": D(0)})
        g["cantidad"] += 1
        g["deuda"] += dinero(r["Deuda"])
        g["credito"] += dinero(r["Credito"])
        por_anio[r["Fecha"][:4]] += dinero(r["Credito"]) - dinero(r["Deuda"])
    saldo = sum(por_anio.values())
    if saldo != D("5739479.4089"):
        raise ValueError("La instantánea no es la del saldo analizado")
    faltantes, posteriores = [], []
    for a in avisos:
        if a["Subject"].startswith("RE:"):
            continue
        p = re.search(r"(\d{1,2})/(20\d{2})", a["Subject"])
        periodo = f"{int(p[1]):02} {p[2]}"
        m = re.search(r"(?is)F\s*\.?\s*931[^\d]{0,100}([\d.]+,\d{2})", a["Body"])
        if m is None:
            raise ValueError("Aviso sin importe F931")
        importe = monto_es(m[1])
        fuente = a["EntryID"]
        if periodo == "07 2025":
            # No trasladar el importe copiado del mes anterior: corrección expresa.
            correccion = next(x for x in avisos if x["Subject"].startswith("RE:") and "07/2025" in x["Subject"])
            if "738.792,95" not in correccion["Body"] or "el valor del vep es el correcto" not in correccion["Body"]:
                raise ValueError("No se corroboró la rectificación del aviso de julio")
            importe, fuente = D("738792.95"), correccion["EntryID"]
        if any(i["IdTipoImpuesto"] == 2 and i["Periodo liquidado"] == periodo for i in wc["impuestos"]):
            continue
        mes, anio = int(p[1]), int(p[2])
        siguiente = f"{anio + (mes == 12)}-{1 if mes == 12 else mes + 1:02}"
        pagos = [{"id": b["IdMovimiento"], "fecha": b["Fecha"][:10], "importe": b["Débitos"]}
                 for b in wc["galicia"] if b["Fecha"].startswith(siguiente) and dinero(b["Débitos"]) == importe]
        fila = {"periodo": periodo, "importeAvisado": importe, "fechaAviso": a["Date"], "fuenteMail": fuente,
                "pagosExactos": pagos, "necesitaDDJJ_VEP": True}
        (posteriores if siguiente > "2026-09" else faltantes).append(fila)

    # Reintegros: grupos disjuntos y cronología de certificados anterior al abono.
    pendientes = {c["IdRetencion"]: c for c in certificados
                  if c["Fecha"] >= "2024" and dinero(c["Importe Devolucion"]) == 0 and dinero(c["Importe Retenido"]) > 0}
    grupos = []
    for b in wc["galicia"]:
        if b["Fecha"] < "2024" or "SNP" not in (b["Descripción"] or "").upper() or dinero(b["Créditos"]) <= 0:
            continue
        disponibles = [c for c in pendientes.values() if c["Fecha"] <= b["Fecha"]]
        if len(disponibles) > 20:
            raise ValueError("Limitar búsqueda antes de enumerar combinaciones")
        matches = []
        for n in range(1, len(disponibles) + 1):
            for combo in itertools.combinations(disponibles, n):
                if sum(dinero(c["Importe Retenido"]) for c in combo) == dinero(b["Créditos"]):
                    matches.append(combo)
        if len(matches) == 1:
            combo = matches[0]
            grupos.append({"galicia": b["IdMovimiento"], "fecha": b["Fecha"][:10], "importe": dinero(b["Créditos"]),
                           "certificados": list(combo), "caracter": "Propuesta por suma exacta única y cronología; sin aplicación SQL"})
            for c in combo:
                del pendientes[c["IdRetencion"]]
        elif len(matches) > 1:
            raise ValueError("Hay más de una agrupación posible: no vincular automáticamente")

    planes = []
    for numero, ejercicio, cuota, desde, hasta, esperado in (
        ("U657364", 2024, D("87297.84"), "2025-07", "2026-06", 12),
        ("W143471", 2025, D("126660.54"), "2026-07", "2026-09", 3),
    ):
        pagos = [{"id": b["IdMovimiento"], "fecha": b["Fecha"][:10], "importe": dinero(b["Débitos"])}
                 for b in wc["galicia"] if desde <= b["Fecha"][:7] <= hasta and dinero(b["Débitos"]) == cuota]
        if len(pagos) != esperado:
            raise ValueError("No coinciden todas las cuotas previstas con el banco")
        if any(dinero(i["Importe"]) == cuota for i in wc["impuestos"]):
            raise ValueError("Revisar la contrapartida del plan antes de darla por faltante")
        planes.append({"plan": numero, "ejercicio": ejercicio, "cuotasPagadas": pagos, "importe": cuota * len(pagos)})
    extras = [b for b in wc["galicia"] if b["IdMovimiento"] in (2647, 2726)]
    informe = {
        "corte": "2026-09-30", "soloLectura": True, "movimientos": len(wc["movimientos"]), "saldoContable": saldo,
        "porOrigen": por_origen, "porAnio": dict(por_anio), "f931Faltantes": faltantes,
        "totalAvisosFaltantesProvisional": sum(x["importeAvisado"] for x in faltantes), "fueraDelCorte": posteriores,
        "reintegrosIdentificadosPropuestos": grupos, "totalReintegrosPropuestos": sum(x["importe"] for x in grupos),
        "certificadosNoAgrupados": list(pendientes.values()), "planesSinObligacionRegistrada": planes,
        "debitosPlanPorIdentificar": extras, "sinCambioDeSaldos": True,
    }
    (ROOT / "analisis.json").write_text(json.dumps(informe, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"saldo": saldo, "f931Faltantes": len(faltantes), "totalAvisosProvisional": informe["totalAvisosFaltantesProvisional"],
                      "reintegros": len(grupos), "certificados": sum(len(x["certificados"]) for x in grupos),
                      "totalReintegros": informe["totalReintegrosPropuestos"], "certificadosSinGrupo": len(pendientes),
                      "planes": [{"plan": p["plan"], "cuotas": len(p["cuotasPagadas"]), "total": p["importe"]} for p in planes]}, default=str, indent=2))


if __name__ == "__main__":
    run()
