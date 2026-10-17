"""036 — Pasos del método para cerrar las 10 fichas casi en cero (Sergio, 2026-10-17).

1. Marca cada "pago sin factura" del detector con la factura que lo respalda: la factura de la cuenta
   más cercana anterior o igual a la fecha del pago (retenciones y cuotas de tarjeta acompañan a su
   factura); Gregec (cliente) con su venta de hacienda 00003-00000009.
2. Confirma el inventario de fuentes (C7).
Los lotes FIFO (cola B) y de doble descuento (cola C) y el cierre se hacen después con la API/pantalla.

Uso (desde backend/): python -m scripts.cierre_fichas_casi_cero_20261017 [--aplicar]
"""

from __future__ import annotations

import sys

from src.db.connection import fetch_all, fetch_one
from src.features.revision_cuentas import evidencia, fichas
from src.features.revision_cuentas.router import _detectar_cuenta, _corte_o_404

USUARIO = "Sergio (036, casi cero 2026-10-17)"
CUENTAS = [522, 485, 493, 467, 492, 176, 578, 41, 282, 23]
GREGEC, VENTA_GREGEC = 485, 99
# Asignaciones puntuales: la cuota Visa del 05/10/2023 de GMRA es de la factura 00835-8303 del 06/10/2023.
FORZADAS = {(492, "tarjetas", 425): 2143514284}


def factura_para(id_contacto: int, fecha) -> dict | None:
    f = fetch_one("SELECT TOP 1 IdDeuda AS id, Fecha AS f, [Nro Documento] AS n FROM dbo.Compras "
                  "WHERE IdContacto = ? AND Fecha <= ? AND ISNULL([Tipo documento], 'Factura') <> 'Nota de Crédito' "
                  "ORDER BY Fecha DESC, IdDeuda DESC", (id_contacto, fecha))
    return f or fetch_one("SELECT TOP 1 IdDeuda AS id, Fecha AS f, [Nro Documento] AS n FROM dbo.Compras "
                          "WHERE IdContacto = ? AND Fecha > ? ORDER BY Fecha, IdDeuda", (id_contacto, fecha))


def main(aplicar: bool) -> None:
    corte = _corte_o_404()
    for c in CUENTAS:
        _, resultado, marcas = _detectar_cuenta(c, corte)
        pendientes = [p for p in resultado["pagos"] if not p.get("marca") or p["marca"].get("estado") == "pendiente"]
        for p in pendientes:
            if c == GREGEC:
                estado, id_compra, kw = "venta-cargada", None, {"tipo_venta": "venta-hacienda", "id_venta": VENTA_GREGEC}
                texto = "venta 00003-00000009"
            else:
                f = factura_para(c, p["fecha"])
                forzada = FORZADAS.get((c, p["medio"], p["idMovimiento"]))
                if forzada:
                    f = fetch_one("SELECT IdDeuda AS id, Fecha AS f, [Nro Documento] AS n FROM dbo.Compras WHERE IdDeuda = ?", (forzada,))
                estado, id_compra, kw = "factura-cargada", f["id"], {}
                texto = f"factura {f['n']} del {str(f['f'])[:10]}"
            print(f"{c}: {p['medio']} {p['idMovimiento']} {p['fecha']} ${p['importe']:,.2f} -> {texto}")
            if aplicar:
                nota = "Pago de la factura (cierre casi cero 17/10/2026)"
                sin_archivo = evidencia.validar_marca(c, estado, nota, id_compra, None, kw.get("tipo_venta"), kw.get("id_venta"))
                fuente = "estado-de-cuenta" if sin_archivo else None
                evidencia.guardar_marca(c, p["medio"], p["idMovimiento"], estado, id_compra, fuente, nota, USUARIO,
                                        kw.get("tipo_venta"), kw.get("id_venta"))
        if aplicar:
            fichas.confirmar_inventario(c, [
                {"tipo": "dropbox", "disponible": True, "detalle": "Facturas en la carpeta de Compras"},
                {"tipo": "extracto", "disponible": True, "detalle": "Extractos bancarios, tarjeta y Mercado Pago"},
                {"tipo": "estado-proveedor", "disponible": False, "detalle": "Sin estado de cuenta del proveedor; saldo 0"},
            ], USUARIO)


if __name__ == "__main__":
    main("--aplicar" in sys.argv)
