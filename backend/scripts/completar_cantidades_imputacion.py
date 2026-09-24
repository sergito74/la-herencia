"""Completa cantidades reconstruibles sin recalcular importes ni aprobaciones.

Solo WC. Por defecto informa una simulación; --aplicar escribe únicamente
Cantidad/Unidad nulas de corridas vigentes que coinciden por completo con el
cálculo actual. Requiere respaldo verificado antes de usar --aplicar.

Uso: .venv\\Scripts\\python.exe -m scripts.completar_cantidades_imputacion [--aplicar]
"""

import argparse

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.imputacion import motor
from src.features.imputacion.cantidades import cantidades_coincidentes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("--limite", type=int, default=2000)
    args = parser.parse_args()
    if not 1 <= args.limite <= 10000:
        parser.error("--limite debe estar entre 1 y 10000")
    _assert_target_is_wc()
    candidatas = fetch_all(
        "SELECT DISTINCT TOP (?) p.IdDetalleCompra AS idDetalleCompra "
        "FROM dbo.ImputacionPropuestas p WHERE p.Origen = 'Insumo' AND p.Cantidad IS NULL "
        "AND p.Estado <> 'RequiereIntervencion' AND p.IdCorrida = ("
        "SELECT TOP 1 p2.IdCorrida FROM dbo.ImputacionPropuestas p2 "
        "WHERE p2.IdDetalleCompra = p.IdDetalleCompra ORDER BY p2.FechaCalculo DESC) "
        "ORDER BY p.IdDetalleCompra", (args.limite,),
    )
    compatibles = filas = 0
    for candidata in candidatas:
        guardadas = fetch_all(
            "SELECT IdPropuesta AS idPropuesta, IdCorrida AS idCorrida, Origen AS origen, "
            "IdDetalleCompra AS idDetalleCompra, IdOrdenTrabajo AS idOrdenTrabajo, "
            "IdLote AS idLote, IdCultivo AS idCultivo, IdCampania AS idCampania, "
            "IdCentroCosto AS idCentroCosto, EsGanaderia AS esGanaderia, "
            "Importe AS importe, Estado AS estado, Cantidad AS cantidad "
            "FROM dbo.ImputacionPropuestas WHERE IdCorrida = ("
            "SELECT TOP 1 IdCorrida FROM dbo.ImputacionPropuestas "
            "WHERE IdDetalleCompra = ? ORDER BY FechaCalculo DESC)",
            (candidata["idDetalleCompra"],),
        )
        calculadas = motor.calcular_propuesta_insumo(candidata["idDetalleCompra"])
        cantidades = cantidades_coincidentes(guardadas, calculadas)
        if not cantidades:
            continue
        compatibles += 1
        statements = []
        for f in guardadas:
            if f["cantidad"] is not None:
                continue
            cantidad = cantidades[f["idPropuesta"]]
            sql = (
                "UPDATE dbo.ImputacionPropuestas SET Cantidad = ?, Unidad = ? "
                "WHERE IdPropuesta = ? AND Cantidad IS NULL AND Importe = ? AND IdCorrida = ("
                "SELECT TOP 1 p2.IdCorrida FROM dbo.ImputacionPropuestas p2 "
                "WHERE p2.IdDetalleCompra = ? ORDER BY p2.FechaCalculo DESC)"
            )
            params = [cantidad["cantidad"], cantidad["unidad"], f["idPropuesta"],
                      f["importe"], f["idDetalleCompra"]]
            for campo, columna in (("idOrdenTrabajo", "IdOrdenTrabajo"), ("idLote", "IdLote"),
                                   ("idCultivo", "IdCultivo"), ("idCampania", "IdCampania"),
                                   ("idCentroCosto", "IdCentroCosto"), ("esGanaderia", "EsGanaderia")):
                if f.get(campo) is None:
                    sql += f" AND {columna} IS NULL"
                else:
                    sql += f" AND {columna} = ?"
                    params.append(f[campo])
            statements.append((sql, tuple(params)))
        filas += len(statements)
        if args.aplicar and statements:
            execute_write_transaction(statements)
    print(f"{'Aplicación' if args.aplicar else 'Simulación'}: {len(candidatas)} corridas revisadas, "
          f"{compatibles} coincidentes, {filas} filas candidatas a completar.")


if __name__ == "__main__":
    main()
