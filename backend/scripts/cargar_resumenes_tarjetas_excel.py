"""Carga los resúmenes de tarjeta (Visa Galicia / Corporativa Nacion) que
faltan en `WC`, a partir de los archivos Excel que exporta cada banco
("Resumen" = cabecera por resumen, "Detalle Resumen" = líneas de consumo).

Compara `Nro. Resumen`/`Nro. Liquidacion` del Excel contra
`Tarjetas_Resumenes.ResumenCodigo` para esa tarjeta y solo inserta los que
todavía no existen — nunca toca un resumen ya cargado (idempotente: correr
dos veces no duplica nada, el segundo dry-run debería reportar 0 faltantes).

Mapeo de columnas de cabecera confirmado contra datos reales ya cargados
(mismo patrón que usan los resúmenes existentes de cada tarjeta):
- Visa Galicia: Impuesto Sellos, Com. Mant. Cuenta, Com. Renov. Anual, IVA,
  INTERES COMP., PERCEP.IVA RG2408, PERCEP. IIBB, Ajuste Res. Anterior
  → ImpuestoSellos, MantCuenta, RenovAnual, IVA21, IntCompens, PercepIVA21,
  PercepIIBB, AjusteResAnterior.
- Corporativa Nacion: mismo esquema sin "INTERES COMP." ni "PERCEP.IVA
  RG2408" (esos campos quedan NULL, igual que en los resúmenes ya
  cargados de esta tarjeta).

Las líneas de consumo intentan resolver `Proveedor` (texto libre del
banco) contra `Contactos.[Razon Social]` por coincidencia exacta
(case-insensitive, sin espacios de más) — sin adivinar por similitud. Sin
match, `IdContacto` queda NULL (igual que cualquier línea sin proveedor
resuelto hoy) para que se vincule a mano después, en vez de arriesgar una
asignación incorrecta.

Un resumen sin ninguna línea de consumo en el Excel (`Total Consumos = 0`)
se carga con `SoloCabecera = 1`, igual que el resto del esquema.

Por defecto corre en modo DRY-RUN. Requiere `--apply` para escribir, y aun
así NO EJECUTAR sin backup de `WC` verificado (Constitución, Principio II).

Uso (desde backend/):
  .venv\\Scripts\\python.exe -m scripts.cargar_resumenes_tarjetas_excel                # dry-run, ambas tarjetas
  .venv\\Scripts\\python.exe -m scripts.cargar_resumenes_tarjetas_excel --apply         # escribe
"""

from __future__ import annotations

import argparse
from datetime import datetime

import openpyxl

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all

VISA_GALICIA = {
    "id_tarjeta": 4,
    "nombre": "Visa Galicia",
    "archivo": r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Bancos\Galicia\Tarjetas\Visa\Detalle Consumos Tarjeta Visa Galicia.xlsx",
    "cargos": {
        "Impuesto Sellos": "ImpuestoSellos",
        "Com. Mant. Cuenta": "MantCuenta",
        "Com. Renov. Anual": "RenovAnual",
        "IVA": "IVA21",
        "INTERES COMP.": "IntCompens",
        "PERCEP.IVA RG2408": "PercepIVA21",
        "PERCEP. IIBB": "PercepIIBB",
        "Ajuste Res. Anterior": "AjusteResAnterior",
    },
}

CORPORATIVA_NACION = {
    "id_tarjeta": 2,
    "nombre": "Corporativa Nacion",
    "archivo": r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Bancos\BNA\Corporativa Nacion\Detalle Consumos Tarjeta Coroporativa Nacion.xlsx",
    "cargos": {
        "Impuesto Sellos": "ImpuestoSellos",
        "Com. Mant. Cuenta": "MantCuenta",
        "Com. Renov. Anual": "RenovAnual",
        "IVA": "IVA21",
        "Percepcion IIBB": "PercepIIBB",
    },
}

TARJETAS = [VISA_GALICIA, CORPORATIVA_NACION]


def _leer_hoja(path: str, hoja: str) -> tuple[list[str], list[tuple]]:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[hoja]
    filas = list(ws.iter_rows(min_row=1, values_only=True))
    encabezado = [str(c) if c is not None else "" for c in filas[0]]
    return encabezado, filas[1:]


def _resumenes_existentes(id_tarjeta: int) -> set[str]:
    return {
        r["ResumenCodigo"]
        for r in fetch_all("SELECT ResumenCodigo FROM dbo.Tarjetas_Resumenes WHERE IdTarjeta = ?", (id_tarjeta,))
    }


def _mapa_contactos() -> dict[str, int]:
    filas = fetch_all("SELECT IdContacto, [Razon Social] AS razon FROM dbo.Contactos")
    return {f["razon"].strip().lower(): f["IdContacto"] for f in filas if f["razon"]}


def _procesar_tarjeta(tarjeta: dict, contactos: dict[str, int]) -> list[dict]:
    encabezado_cab, filas_cab = _leer_hoja(tarjeta["archivo"], "Resumen")
    encabezado_det, filas_det = _leer_hoja(tarjeta["archivo"], "Detalle Resumen")
    idx_cab = {nombre: i for i, nombre in enumerate(encabezado_cab)}
    idx_det = {nombre: i for i, nombre in enumerate(encabezado_det)}

    existentes = _resumenes_existentes(tarjeta["id_tarjeta"])

    lineas_por_resumen: dict[str, list[tuple]] = {}
    for fila in filas_det:
        if fila[idx_det["Resumen Numero" if "Resumen Numero" in idx_det else "Nro. Liquidacion"]] is None:
            continue
        codigo = str(fila[idx_det["Resumen Numero" if "Resumen Numero" in idx_det else "Nro. Liquidacion"]])
        lineas_por_resumen.setdefault(codigo, []).append(fila)

    resultado = []
    for fila in filas_cab:
        campo_codigo = "Nro. Resumen" if "Nro. Resumen" in idx_cab else "Nro. Liquidacion"
        if fila[idx_cab[campo_codigo]] is None:
            continue
        codigo = str(fila[idx_cab[campo_codigo]])
        if codigo in existentes:
            continue

        cargos = {}
        for col_excel, col_db in tarjeta["cargos"].items():
            if col_excel in idx_cab:
                cargos[col_db] = fila[idx_cab[col_excel]] or 0

        lineas_excel = lineas_por_resumen.get(codigo, [])
        lineas = []
        for l in lineas_excel:
            proveedor = l[idx_det["Proveedor"]]
            id_contacto = contactos.get(proveedor.strip().lower()) if proveedor else None
            lineas.append(
                {
                    "fechaCompra": l[idx_det["Fecha Compra"]],
                    "detalle": (l[idx_det["Detalle"]] or "")[:255],
                    "importe": l[idx_det["Importe"]] or 0,
                    "proveedorExcel": proveedor,
                    "idContacto": id_contacto,
                    "nroDocumento": (
                        (str(l[idx_det["Nro. Factura"]])[:50] or None) if "Nro. Factura" in idx_det and l[idx_det["Nro. Factura"]] else None
                    ),
                }
            )

        resultado.append(
            {
                "idTarjeta": tarjeta["id_tarjeta"],
                "tarjetaNombre": tarjeta["nombre"],
                "resumenCodigo": codigo,
                "fechaCierre": fila[idx_cab["Fecha Cierre"]],
                "fechaVencimiento": fila[idx_cab["Fecha Vencimiento"]],
                "cargos": cargos,
                "lineas": lineas,
                "soloCabecera": len(lineas) == 0,
            }
        )
    return resultado


def _imprimir_resumen(faltantes: list[dict]) -> None:
    for tarjeta in TARJETAS:
        de_esta_tarjeta = [f for f in faltantes if f["idTarjeta"] == tarjeta["id_tarjeta"]]
        total_lineas = sum(len(f["lineas"]) for f in de_esta_tarjeta)
        sin_proveedor = sum(1 for f in de_esta_tarjeta for l in f["lineas"] if l["idContacto"] is None)
        print(f"{tarjeta['nombre']}: {len(de_esta_tarjeta)} resúmenes faltantes, {total_lineas} líneas ({sin_proveedor} sin proveedor resuelto)")
        for f in de_esta_tarjeta:
            print(f"  {f['resumenCodigo']} · cierre {f['fechaCierre']:%Y-%m-%d} · {len(f['lineas'])} líneas" + (" · SOLO CABECERA" if f["soloCabecera"] else ""))


def _aplicar(faltantes: list[dict]) -> None:
    for f in faltantes:
        columnas_cargo = list(f["cargos"].keys())
        placeholders_cargo = ", ".join("?" for _ in columnas_cargo)
        columnas_sql = ", ".join(["IdTarjeta", "ResumenCodigo", "FechaCierre", "FechaVencimiento", "EstadoResumen", "SoloCabecera", "Observaciones"] + columnas_cargo)
        valores = [
            f["idTarjeta"],
            f["resumenCodigo"],
            f["fechaCierre"],
            f["fechaVencimiento"],
            "Cargado",
            1 if f["soloCabecera"] else None,
            f"Importado desde Excel el {datetime.now():%Y-%m-%d}",
        ] + [f["cargos"][c] for c in columnas_cargo]
        placeholders = ", ".join("?" for _ in valores)

        statements: list = [
            (
                f"INSERT INTO dbo.Tarjetas_Resumenes ({columnas_sql}) OUTPUT INSERTED.IdResumen VALUES ({placeholders})",
                tuple(valores),
            )
        ]
        for l in f["lineas"]:
            statements.append(
                (
                    lambda resultados, l=l: (
                        "INSERT INTO dbo.Tarjetas_Resumenes_Lineas "
                        "(IdResumen, FechaCompra, Detalle, Importe, IdContacto, NroDocumento) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (resultados[0], l["fechaCompra"], l["detalle"], l["importe"], l["idContacto"], l["nroDocumento"]),
                    )
                )
            )
        execute_write_transaction(statements)
        print(f"  Insertado {f['resumenCodigo']} ({f['tarjetaNombre']}) con {len(f['lineas'])} líneas.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Escribe en WC (default: dry-run)")
    args = parser.parse_args()

    _assert_target_is_wc()

    contactos = _mapa_contactos()
    faltantes: list[dict] = []
    for tarjeta in TARJETAS:
        faltantes.extend(_procesar_tarjeta(tarjeta, contactos))

    _imprimir_resumen(faltantes)

    if args.apply:
        _aplicar(faltantes)
        print(f"\nAplicados {len(faltantes)} resúmenes nuevos.")
    else:
        print("\nDry-run: no se escribió nada. Correr con --apply para cargar (requiere backup de WC verificado).")


if __name__ == "__main__":
    main()
