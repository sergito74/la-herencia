"""Conciliación de la compra de Mercado Libre del 13/11/2025 (#2000009998103567), 2026-10-02.

Cargo Visa Galicia (línea 713) $110.760,27, 42 productos de ~15 vendedores.
Reembolso total $49.128,41 en 10 líneas de reintegro. Cuadre al centavo:

- 12 facturas de productos conservados ................. $61.631,85
- 2 facturas de productos facturados y reintegrados .... $ 9.791,41
  (First Label 0004-01691859 jabón Ace; Simplex 00001-02467240 fideos + jabón Lux)
- productos reintegrados nunca facturados (7 líneas) .... $39.337,00

Acciones (aprobadas por Sergio):
1. NC "SIN DOCUMENTO" (nro SD-<factura>) por los productos facturados y
   reintegrados, con los mismos renglones en negativo.
2. Línea 713 → las 14 facturas; el resto ($39.337,01) "sin documento"
   (compensado por los 7 reintegros sin facturar).
3. Los 7 reintegros sin facturar → "sin documento".
4. Reintegro 720 → NC First Label; reintegros 729 y 4738 → NC Simplex.

Idempotente en lo posible (no recrea NC existentes). Respaldo verificado.
Uso (desde backend/): .venv/Scripts/python.exe -m scripts.conciliar_compra_ml_20251113
"""

from src.db.connection import fetch_one
from src.features.compras import repository as C
from src.features.tarjetas_resumenes import repository as R
from src.features.vinculos.backup import backup_verificado

LINEA_CARGO = 713
FACTURAS = [2143515250, 2143515244, 2143515248, 2143515245, 2143515247, 2143515249, 2143515266,
            2143521541, 2143515246, 2143515252, 2143515253, 2143515254, 2143515255, 2143515256]
REINTEGROS_SIN_FACTURA = [714, 721, 722, 723, 724, 725, 726]
REF = "Compra Mercado Libre #2000009998103567 del 13/11/2025"
NC = [  # (factura origen, fecha del reintegro, líneas de reintegro)
    (2143515244, "2025-11-18", [720]),
    (2143521541, "2025-11-21", [729, 4738]),
]


def _crear_nc(id_factura: int, fecha: str) -> int:
    cab = C.get_compra_cabecera(id_factura)
    nro = "SD-" + cab["numeroDocumento"].split("-")[-1].strip()
    existe = fetch_one("SELECT IdDeuda FROM dbo.Compras WHERE IdContacto = ? AND [Nro Documento] = ?",
                       (cab["proveedor"]["idContacto"], nro))
    if existe:
        return existe["IdDeuda"]
    cabecera = {
        "idContacto": cab["proveedor"]["idContacto"], "fecha": fecha, "tipo": cab["tipo"] or "A",
        "tipoDocumento": "Nota de Crédito", "numeroDocumento": nro, "moneda": "Pesos", "tipoDeCambio": 1.0,
        "ingresosBrutos": 0, "conceptosNoGravados": 0, "guias": 0, "comision": 0, "financiacion": 0,
        "gastosVarios": 0, "leyDeSellos": 0, "resGral4169": 0, "ajustaTipoCambio": False,
        "documentoOriginal": None,
    }
    lineas = [{
        "productoServicio": l["productoServicio"], "cantidad": l["cantidad"], "precioUnitario": -abs(l["precioUnitario"]),
        "iva": l["iva"], "unidad": None, "idCentroCosto": l["imputacion"]["idCentroCosto"],
        "idDestino": l["imputacion"]["idDestino"], "idRubro": l["imputacion"]["idRubro"],
        "campaña": l["imputacion"]["campania"], "ajusteFinanciero": False,
    } for l in C.get_lineas_compra(id_factura)]
    return C.create_compra(cabecera, lineas, [])


def main() -> None:
    print(f"Respaldo verificado: {backup_verificado('compra-ml-20251113')}")
    ncs = {}
    for factura, fecha, lineas in NC:
        ncs[factura] = _crear_nc(factura, fecha)
        print(f"NC para factura {factura}: {ncs[factura]}")
    if not R.get_compras_vinculadas(LINEA_CARGO):
        R.vincular_compras_lote(LINEA_CARGO, FACTURAS)
    if not R.get_estado(LINEA_CARGO):
        R.marcar_sin_documento(LINEA_CARGO, "Otro",
                               f"{REF}: el resto son productos reintegrados sin facturar (líneas {REINTEGROS_SIN_FACTURA}).")
    for l in REINTEGROS_SIN_FACTURA:
        if not R.get_estado(l):
            R.marcar_sin_documento(l, "Otro", f"{REF}: reintegro de producto nunca facturado (compensa la línea {LINEA_CARGO}).")
    for factura, _, lineas in NC:
        for l in lineas:
            if not R.get_compras_vinculadas(l):
                R.vincular_compras_lote(l, [ncs[factura]])
    for l in [LINEA_CARGO, 720, 729, 4738]:
        print(l, [(v.get("idCompra"), v.get("importeImputado")) for v in R.get_compras_vinculadas(l)], R.get_estado(l))


if __name__ == "__main__":
    main()
