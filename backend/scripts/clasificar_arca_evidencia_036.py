"""Clasificar metadatos con evidencia ya reunida, sin registrar pagos u obligaciones.

Por defecto simula. --aplicar toma backup verificado; repetible sin nuevas filas.
Las devoluciones se clasifican como IVA: NO se aplican aún a certificados.
"""
import json
import sys
from decimal import Decimal as D
from pathlib import Path

from src.db.connection import reconciliation_transaction
from src.features.cuentas_corrientes import arca
from src.features.vinculos.backup import backup_verificado

ROOT = Path(__file__).resolve().parents[2] / "backups/arca-analisis-20261025"


def main():
    analisis = json.loads((ROOT / "analisis.json").read_text(encoding="utf-8"))
    filas, marcas = arca.cargar()
    originales = {(f["origen"], f["idOrigen"]): f for f in filas}
    propuestas = []
    for grupo in analisis["reintegrosIdentificadosPropuestos"]:
        propuestas.append((grupo["galicia"], grupo["importe"], "iva", "deuda",
                           "Reintegro IVA: abono AFIP SNP y suma exacta de certificados; análisis 036 del 25/10. Solo clasificación; sin aplicar devolución a certificados."))
    for plan in analisis["planesSinObligacionRegistrada"]:
        for pago in plan["cuotasPagadas"]:
            propuestas.append((pago["id"], pago["importe"], "bienes-sustitutos", "credito",
                               f"Plan {plan['plan']}, Bienes Sustitutos {plan['ejercicio']}: cuota pagada confirmada en Mis Facilidades 25/10 y banco. Solo clasificación del pago existente."))
    pendientes = []
    for ident, importe, clave, lado, motivo in propuestas:
        key = ("Galicia", ident)
        fila = originales[key]
        otro = "deuda" if lado == "credito" else "credito"
        if D(str(fila[lado])) != D(importe) or D(str(fila[otro])) != 0:
            raise ValueError(f"Cambió el movimiento Galicia {ident}; no clasificar")
        if clave == "iva" and "SNP" not in fila["detalle"].upper():
            raise ValueError("El abono no identifica SNP")
        partes = [{"subcuenta":clave,"deuda":str(fila["deuda"]),"credito":str(fila["credito"])}]
        marca = marcas.get(key, {})
        existente = json.loads(marca.get("reparto") or "[]")
        if existente:
            igual = len(existente)==1 and existente[0]["subcuenta"]==clave and D(existente[0][lado])==D(importe) and D(existente[0][otro])==0
            if igual:
                continue
            raise ValueError(f"Hay otra clasificación manual en Galicia {ident}; no sobrescribir")
        pendientes.append({"origen":"Galicia","idOrigen":ident,"version":marca.get("version",0),"partes":partes,"motivo":motivo})
    print(json.dumps({"propuestas":len(propuestas),"pendientes":len(pendientes),"soloMetadatos":True}))
    if "--aplicar" not in sys.argv or not pendientes:
        return
    respaldo = backup_verificado("arca-clasificaciones-036")
    antes = arca.construir(filas, marcas)
    cambios = []
    with reconciliation_transaction():
        for p in pendientes:
            resultado = arca.guardar(p["origen"],p["idOrigen"],p["version"],p["partes"],p["motivo"],"Codex - clasificación documental 036")
            cambios.append({**p,**resultado})
        actuales, marcas_actuales = arca.cargar()
        despues = arca.construir(actuales, marcas_actuales)
        if actuales != filas or antes["saldoTotal"] != despues["saldoTotal"] or antes["total"] != despues["total"]:
            raise RuntimeError("Cambió el libro original; revertir transacción de clasificación")
    resultado={"backup":respaldo,"clasificaciones":cambios,"saldoAntes":antes["saldoTotal"],"saldoDespues":despues["saldoTotal"],"movimientos":antes["total"],"soloMetadatos":True}
    (ROOT / "clasificaciones-aplicadas.json").write_text(json.dumps(resultado,default=str,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"aplicadas":len(cambios),"backup":respaldo,"saldo":despues["saldoTotal"]},default=str))


if __name__ == "__main__":
    main()
