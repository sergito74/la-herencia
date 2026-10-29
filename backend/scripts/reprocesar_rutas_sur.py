"""Relee facturas de Rutas Sur y repara sus avisos. Por defecto solo simula.

Desde backend: python -m scripts.reprocesar_rutas_sur [--aplicar] [PDF ...]
No elimina compras ni contactos. Se detiene si encuentra identidades duplicadas.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

from src.db.connection import fetch_all, fetch_one, execute_write, reconciliation_transaction
from src.features.boveda import carga
from src.features.boveda.conectores import DocumentoPortal, cargar_conectores
from src.features.compras import repository as compras
from src.features.descarga_peajes import lectores
from src.features.descarga_peajes.carga import armar_compra
from src.features.vinculos.backup import backup_verificado

NOMBRE = "Rutas Sur Atlantico S.A."
CONTACTO = 2657


def centavos(valor):
    return Decimal(str(valor)).quantize(Decimal("0.01"), ROUND_HALF_UP)


def ejecutar(rutas: list[Path], aplicar: bool = False):
    contactos = fetch_all("SELECT IdContacto AS id, [Razon Social] AS nombre FROM dbo.Contactos "
                          "WHERE [Razon Social] LIKE '%Corresur%' OR "
                          "REPLACE(REPLACE([CUIT/CUIL], '-', ''), ' ', '') = ?", ("30719454190",))
    if len(contactos) != 1 or contactos[0]["id"] != CONTACTO or contactos[0]["nombre"] != NOMBRE:
        raise ValueError("Revisar la identidad de Rutas Sur antes de continuar")
    conector = cargar_conectores()["telepeajeplus"]
    preparados = []
    for ruta in rutas:
        pdf = ruta.read_bytes()
        leido = lectores.leer(NOMBRE, lectores.texto_pdf(pdf))
        cabecera, lineas = armar_compra(leido, CONTACTO, str(ruta))
        if centavos(compras.calcular_totales(lineas, cabecera)["importeTotal"]) != centavos(leido.total_impreso):
            raise ValueError(f"No cierra al centavo: {ruta.name}")
        existente = fetch_one("SELECT IdDeuda AS id FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?",
                              (CONTACTO, leido.numero))
        if existente:
            guardado = compras.get_compra_cabecera(existente["id"])
            detalle = compras.get_lineas_compra(existente["id"])
            if centavos(compras.calcular_totales(detalle, guardado)["importeTotal"]) != centavos(leido.total_impreso):
                raise ValueError(f"La compra existente difiere del PDF: {leido.numero}")
        print(f"{leido.numero} | {leido.fecha} | {leido.total_impreso:.2f} | "
              f"{'ya cargada' if existente else 'para cargar'}")
        preparados.append((ruta, pdf, leido))
    if not aplicar:
        return
    print("Respaldo verificado:", backup_verificado("rutas-sur-20261029"))
    with reconciliation_transaction():
        for ruta, pdf, leido in preparados:
            doc = DocumentoPortal(clave=f"reproceso:{leido.numero}", fecha=leido.fecha, tipo="factura",
                                  proveedor=NOMBRE, bajar=lambda: pdf, id_contacto=CONTACTO)
            resultado = carga.cargar(conector, doc, pdf, str(ruta))
            if resultado["estadoCarga"] not in ("cargado_auto", "ya_cargado"):
                raise ValueError(str(resultado))
            id_compra = resultado["idCompra"]
            for tabla in ("Portales_Documentos", "DescargaPeajes_Documentos"):
                execute_write(f"UPDATE dbo.{tabla} SET Proveedor = ?, IdContacto = ?, FechaDocumento = ?, "
                              "NumeroDocumento = ?, TotalImpreso = ?, EstadoCarga = ?, Motivo = NULL, IdCompra = ? "
                              "WHERE Ruta = ? AND IdContacto = ?",
                              (NOMBRE, CONTACTO, leido.fecha, leido.numero, leido.total_impreso,
                               resultado["estadoCarga"], id_compra, str(ruta), CONTACTO))
            execute_write("UPDATE dbo.DocumentosNuevos SET Numero = ?, Fecha = ?, Total = ?, "
                          "Estado = 'cargado_solo', Motivo = NULL, IdRegistro = ? "
                          "WHERE Ruta = ? AND IdContacto = ? AND Estado = 'para_cargar'",
                          (leido.numero, leido.fecha, leido.total_impreso, id_compra, str(ruta), CONTACTO))
        for tabla in ("Portales_Documentos", "DescargaPeajes_Documentos"):
            execute_write(f"UPDATE dbo.{tabla} SET Proveedor = ? WHERE Proveedor = 'Corresur' AND IdContacto = ?",
                          (NOMBRE, CONTACTO))
    print("Facturas y avisos actualizados sin duplicar compras.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("pdf", nargs="*", type=Path)
    args = parser.parse_args()
    carpeta = Path.home() / "Dropbox/Giamigli de Bolivar SA/Compras/04 2026 - 03 2027"
    ejecutar(args.pdf or [carpeta / "20261028_Corresur.pdf", carpeta / "20261028_Corresur 001.pdf"], args.aplicar)
