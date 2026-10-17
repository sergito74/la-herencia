"""036 — Pasos del método para cerrar una cuenta ya llevada a cero (decisiones de Sergio, 2026-10-17).

Uso (desde backend/):
    python -m scripts.cerrar_cuenta_036 <idContacto> --nota "<motivo del cierre>" [--tc-pactado "<motivo>"]
           [--sin-estado "<motivo>"] [--fuente dropbox,extracto,...]

1. `--tc-pactado`: regla de la 035 (los pagos en pesos se pasan a dólares al TC de las facturas).
2. Marca cada pago "sin factura" con la factura anterior más cercana (o la siguiente si no hay anterior).
3. Confirma el inventario de fuentes. `--sin-estado` registra que no hay estado de cuenta del proveedor (evidencia C3).
4. Si faltan imputaciones (C5), aplica el lote FIFO solo a esta cuenta.
5. Cierra la ficha (si falta algún criterio, lo informa y no cierra).
"""

from __future__ import annotations

import argparse
from datetime import date

from src.db.connection import fetch_one
from src.features.auditoria_cuentas import bimonetaria, conocidos
from src.features.revision_cuentas import criterios, evidencia, fichas, lotes
from src.features.revision_cuentas.router import _corte_o_404, _detectar_cuenta

U = "Sergio (036, cierres 2026-10-17)"


def factura_para(id_contacto: int, fecha, importe: float | None = None) -> dict | None:
    """Primero la factura de ±60 días cuyo importe (en pesos, al TC de la factura) coincide con el pago; si no, la anterior más cercana."""
    if importe:
        f = fetch_one("SELECT TOP 1 c.IdDeuda AS id FROM dbo.Compras c JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda "
                      "WHERE c.IdContacto = ? AND ABS(DATEDIFF(day, c.Fecha, ?)) <= 60 "
                      "AND ABS(v.ImporteDocumento * CASE WHEN c.Moneda = 'Dolares' THEN ISNULL(c.[Tipo de Cambio], 1) ELSE 1 END - ?) <= 1 "
                      "ORDER BY ABS(DATEDIFF(day, c.Fecha, ?))", (id_contacto, fecha, abs(importe), fecha))
        if f:
            return f
    f = fetch_one("SELECT TOP 1 IdDeuda AS id FROM dbo.Compras WHERE IdContacto = ? AND Fecha <= ? "
                  "AND ISNULL([Tipo documento], 'Factura') <> 'Nota de Crédito' ORDER BY Fecha DESC, IdDeuda DESC", (id_contacto, fecha))
    return f or fetch_one("SELECT TOP 1 IdDeuda AS id FROM dbo.Compras WHERE IdContacto = ? AND Fecha > ? ORDER BY Fecha, IdDeuda",
                          (id_contacto, fecha))


def faltantes(c: int, corte) -> list[dict]:
    ctx = fichas.cargar_contexto(c, corte)
    return criterios.faltantes_para_cerrar(criterios.evaluar(ctx["criterios_ctx"]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("contacto", type=int)
    ap.add_argument("--nota", required=True)
    ap.add_argument("--tc-pactado")
    ap.add_argument("--sin-estado")
    ap.add_argument("--fuente", default="dropbox,extracto")
    a = ap.parse_args()
    c, corte = a.contacto, _corte_o_404()

    if a.tc_pactado and not any(x["tipo"] == "tc-pactado" and x["clave"] == str(c) for x in conocidos.listar()):
        conocidos.crear("tc-pactado", str(c), a.tc_pactado, None, U)
        bimonetaria.invalidar()
    _, resultado, _ = _detectar_cuenta(c, corte)
    ya = evidencia.leer_marcas(c)  # el detector no trae las marcas: no pisar las que ya existen
    for p in resultado["pagos"]:
        if (ya.get((p["medio"], p["idMovimiento"])) or {}).get("estado", "pendiente") == "pendiente":
            f = factura_para(c, p["fecha"], p.get("importe"))
            if f:
                try:
                    sin_archivo = evidencia.validar_marca(c, "factura-cargada", None, f["id"], None)
                except ValueError:  # factura sin PDF: se respalda con el estado de cuenta (FR-020)
                    sin_archivo = evidencia.validar_marca(c, "factura-cargada", None, f["id"], "estado-de-cuenta")
                evidencia.guardar_marca(c, p["medio"], p["idMovimiento"], "factura-cargada", f["id"],
                                        "estado-de-cuenta" if sin_archivo else None, "Pago de la factura (cierre 17/10/2026)", U)
                print("marcado", p["medio"], p["idMovimiento"], p["importe"], "-> compra", f["id"])
    detalles = {"dropbox": "Facturas en la carpeta de Compras", "extracto": "Extractos bancarios / tarjeta / Mercado Pago",
                "estado-proveedor": "Estado de cuenta del proveedor", "certificado": "Certificados de retención"}
    fichas.confirmar_inventario(c, [{"tipo": t, "disponible": True, "detalle": detalles.get(t)} for t in a.fuente.split(",")], U)
    if a.sin_estado:
        evidencia.crear_saldo_externo(c, corte if isinstance(corte, date) else date.fromisoformat(str(corte)), 0.0,
                                      "Pesos", "sin-estado", None, a.sin_estado, U)
    if any(x["codigo"] == "C5" for x in faltantes(c, corte)):
        lote = lotes.simular("B", "fifo-tandas", U)
        if c in {x["idContacto"] for x in lote["cuentas"]}:
            lotes.tildar(lote["idCorreccion"], [c], False)
            print("FIFO lote", lote["idCorreccion"], lotes.aplicar(lote["idCorreccion"], U).get("estado"))
        else:
            lotes.descartar(lote["idCorreccion"])
            print("FIFO: la cuenta no está entre las candidatas del lote")
    falta = faltantes(c, corte)
    if falta:
        print("NO SE CIERRA, faltan:", [(x["codigo"], x["medido"]) for x in falta])
        return
    f = fichas.cambiar_estado(c, {"estado": "cerrada", "nota": a.nota}, U)
    print(c, f["estado"], "saldo", f.get("saldoAlCorte"), f.get("moneda"))


if __name__ == "__main__":
    main()
