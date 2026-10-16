"""037 — Lectores de PDF de peajes contra comprobantes reales.

Los PDFs no se versionan (datos personales): se leen de la carpeta de Compras
de Dropbox según `fixtures/peajes/casos.json` y el caso se saltea si no está.
No escribe en WC ni entra a portales.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from src.features.compras.repository import calcular_totales
from src.features.descarga_peajes import lectores
from src.features.descarga_peajes.carga import TOLERANCIA, armar_compra

COMPRAS = Path.home() / "Dropbox" / "Giamigli de Bolivar SA" / "Compras"
CASOS = json.loads((Path(__file__).parent / "fixtures" / "peajes" / "casos.json").read_text(encoding="utf-8"))["casos"]


def _texto(caso: dict) -> str:
    ruta = COMPRAS / caso["archivo"]
    if not ruta.exists():
        pytest.skip(f"PDF no disponible: {caso['archivo']}")
    return lectores.texto_pdf(ruta.read_bytes())


def _total(leido: lectores.Leido) -> float:
    cabecera, lineas = armar_compra(leido, 1, "x.pdf")
    return calcular_totales(lineas, cabecera)["importeTotal"]


@pytest.mark.parametrize("caso", CASOS, ids=[c["archivo"].split("/")[-1] for c in CASOS])
def test_lector_lee_y_cierra(caso):
    leido = lectores.leer(caso["proveedor"], _texto(caso))
    esperado = caso["esperado"]
    assert leido.numero == esperado["numero"]
    assert leido.fecha == date.fromisoformat(esperado["fecha"])
    assert leido.total_impreso == pytest.approx(esperado["total"], abs=0.005)
    assert abs(_total(leido) - leido.total_impreso) <= TOLERANCIA


def test_importe_alterado_no_cierra():
    caso = next(c for c in CASOS if c["proveedor"] == "Ceamse")
    leido = lectores.leer("Ceamse", _texto(caso))
    leido.renglones[0]["precioUnitario"] += 10
    assert abs(_total(leido) - leido.total_impreso) > TOLERANCIA


def test_nota_de_credito_queda_pendiente():
    with pytest.raises(lectores.NoReconocido, match="nota de crédito"):
        lectores.leer("AutopistasDelSol", "NOTA DE CREDITO\nA\n0840-00000001\nFecha: 01/10/26")


def test_formato_desconocido():
    with pytest.raises(lectores.NoReconocido):
        lectores.leer("AutopistasDelSol", "un texto cualquiera sin factura")
    with pytest.raises(lectores.NoReconocido):
        lectores.leer("ProveedorNuevo", "x")


def test_telepeaje_con_concepto_no_previsto_queda_pendiente():
    texto = ("Nº: 0002-111111111 Sucursal\nCierre: 12/10/2026\nOTROS CONCEPTOS\n"
             "Intereses Punitorios 12/10/2026 $ 5.00\nTotal otros conceptos $ 5.00\n")
    with pytest.raises(lectores.NoReconocido):
        lectores.leer("Telepeaje", texto)


@pytest.mark.parametrize("valor,esperado", [("1.971,88", 1971.88), ("1,239.67", 1239.67), ("1074.38", 1074.38),
                                            ("0,00", 0.0), ("$ 6,195.28", 6195.28), ("34455,32", 34455.32)])
def test_numero(valor, esperado):
    assert lectores.numero(valor) == esperado
