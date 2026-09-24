"""Compara, renglón por renglón, la clasificación manual (`Det_Compras`,
cargada a mano al comprar) contra la propuesta calculada por el motor de
auto-clasificación (017-imputacion-automatica-costos) — pedido explícito
del usuario, 2026-09-24. Solo lee: no modifica ni `Det_Compras` ni
`ImputacionPropuestas`.

La comparación es por Campaña (lo único que ambas clasificaciones tienen en
común: `Det_Compras.IdCampaña` es un único valor por renglón; el motor puede
repartir un renglón entre varias campañas según el consumo real).

Categorías de resultado, por renglón con al menos una fracción del motor:
- `coincide`: el motor concentra el 100% del importe consumido en la misma
  campaña que la clasificación manual.
- `difiere`: el motor concentra el 100% del importe consumido en UNA
  campaña distinta a la manual.
- `repartido`: el motor divide el renglón entre más de una campaña (la
  manual, por diseño, no puede expresar esto).
- `solo_stock`: todo el importe del motor quedó "en stock sin consumir"
  (nada se imputó todavía a ninguna campaña).

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.comparar_imputacion_manual_vs_motor
"""

from __future__ import annotations

from collections import defaultdict

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

EPS = 1e-6


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT dc.IdDetalleCompra, dc.[IdCampaña], ca.[Campaña]
            FROM dbo.Det_Compras dc
            LEFT JOIN dbo.Campañas ca ON ca.[IdCampaña] = dc.[IdCampaña]
            WHERE dc.IdDetalleCompra IN (SELECT DISTINCT IdDetalleCompra FROM dbo.ImputacionPropuestas WHERE Origen = 'Insumo')
            """
        )
        manual = {row[0]: {"idCampania": row[1], "campania": row[2]} for row in cursor.fetchall()}

        cursor.execute(
            """
            SELECT IdDetalleCompra, IdCampania, Importe
            FROM dbo.ImputacionPropuestas
            WHERE Origen = 'Insumo' AND Estado = 'Aprobada'
            """
        )
        por_renglon: dict[int, list[tuple]] = defaultdict(list)
        for id_detalle, id_campania, importe in cursor.fetchall():
            por_renglon[id_detalle].append((id_campania, float(importe)))

        cursor.execute("SELECT [IdCampaña], [Campaña] FROM dbo.Campañas")
        nombres_campania = {row[0]: row[1] for row in cursor.fetchall()}
    finally:
        conn.close()

    categorias = {"coincide": 0, "difiere": 0, "repartido": 0, "solo_stock": 0}
    diferencias_por_campania: dict[tuple, float] = defaultdict(float)  # (campania_manual, campania_motor) -> $
    ejemplos_difiere: list[dict] = []
    ejemplos_repartido: list[dict] = []

    for id_detalle, fracciones in por_renglon.items():
        m = manual.get(id_detalle, {})
        campania_manual = m.get("idCampania")
        nombre_manual = m.get("campania")

        por_campania: dict[int | None, float] = defaultdict(float)
        for id_campania, importe in fracciones:
            por_campania[id_campania] += importe

        con_campania = {k: v for k, v in por_campania.items() if k is not None and abs(v) > EPS}
        solo_stock_importe = por_campania.get(None, 0.0)

        if not con_campania:
            categorias["solo_stock"] += 1
            continue

        if len(con_campania) > 1:
            categorias["repartido"] += 1
            if len(ejemplos_repartido) < 10:
                reparto_nombres = {nombres_campania.get(k, k): round(v, 2) for k, v in con_campania.items()}
                ejemplos_repartido.append({"idDetalleCompra": id_detalle, "manual": nombre_manual, "reparto": reparto_nombres})
            continue

        (campania_motor, importe_motor), = con_campania.items()
        if campania_motor == campania_manual:
            categorias["coincide"] += 1
        else:
            categorias["difiere"] += 1
            diferencias_por_campania[(nombre_manual, campania_motor)] += importe_motor
            if len(ejemplos_difiere) < 10:
                ejemplos_difiere.append(
                    {
                        "idDetalleCompra": id_detalle,
                        "campaniaManual": nombre_manual,
                        "campaniaMotor": nombres_campania.get(campania_motor, campania_motor),
                        "importe": round(importe_motor, 2),
                    }
                )

    total = sum(categorias.values())
    print(f"Renglones de insumo comparados (con propuesta aprobada del motor): {total} sobre {DATABASE}\n")
    for cat, n in categorias.items():
        pct = (n / total * 100) if total else 0
        print(f"  {cat:12s}: {n:5d}  ({pct:5.1f}%)")

    print("\nRenglones sin ninguna propuesta del motor todavía (no vinculados a remito/consumo):",
          len(manual) - total if manual else "?")

    if ejemplos_difiere:
        print("\nEjemplos donde el motor asigna una campaña distinta a la declarada manualmente:")
        for e in ejemplos_difiere:
            print(f"  renglón {e['idDetalleCompra']}: manual={e['campaniaManual']!r}, motor={e['campaniaMotor']!r}, importe=${e['importe']}")

    if ejemplos_repartido:
        print("\nEjemplos donde el motor reparte un renglón entre varias campañas (la manual no puede expresarlo):")
        for e in ejemplos_repartido:
            print(f"  renglón {e['idDetalleCompra']}: manual={e['manual']!r}, reparto={e['reparto']}")


if __name__ == "__main__":
    main()
