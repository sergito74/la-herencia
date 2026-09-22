"""Migración de datos heredados del módulo Órdenes de Trabajo (011-ordenes-trabajo) a `WC`.

Migra:
  - 153 filas de `Ordenes` -> `Ordenes_Trabajo` (`Estado='Ejecutada'` si `Fecha Ejecucion`
    no es NULL, si no `'Planificada'`; `IdContratistaContacto` se copia tal cual salvo el
    valor heredado `0`, que no referencia ningún contacto real y se trata como NULL
    -maquinaria propia-; la columna `Contratista` -entero 1-13- no se migra).
  - 820 filas de `Ordenes_Detalles` -> `Ordenes_Trabajo_Insumos` (`CantidadTotal` se
    recalcula como la suma de las distribuciones, no se copia `Total Aplicado`).
  - 4.319 filas de `Ordenes_Detalles_Distrib` -> `Ordenes_Trabajo_Distrib`, unificando
    unidades (`LTS`/`LITROS`->`LTS`, `KGS`/`KILOS`->`KGS`, `BOL`->`BOLSA`, `UN`->`UNI`)
    y tomando `Superficie` de `Ordenes_Lotes` (join por Orden+Lote+Cultivo+Campaña; los
    4.319 renglones tienen match, verificado).
  - El flag `Aplicar` de `Ordenes_Lotes` (879 filas) se copia a cada `Ordenes_Trabajo_Distrib`
    que comparte esa combinación Orden+Lote+Cultivo+Campaña.
  - Los renglones donde `CantidadTotal` no cierra contra `Total Aplicado` (tolerancia
    absoluta 0.5, igual que el criterio de cierre exacto de una orden nueva) se migran
    con `RevisarMigracion=1` (13 de 820, verificado).
  - El lote `PRUE` (lote de pruebas, excluido en toda la app) no se migra.
  - `Labores Maquinaria propia` NO se migra a `Ordenes_Trabajo_Maquinaria`: son conceptos
    distintos, la planilla vieja no está vinculada a ninguna orden (data-model.md).

Idempotente a nivel de orden: cada `Ordenes_Trabajo` migrada queda marcada en
`Observaciones` con "Migrado de Orden heredada #<IdOrden>"; una orden ya migrada se
saltea en una corrida posterior.

Por defecto corre en modo DRY-RUN (solo lectura): imprime el plan y no escribe nada.
Requiere `--apply` para escribir, y aun así NO EJECUTAR sin backup de `WC` verificado
y autorización explícita del usuario (Constitución, Principio II).

Uso (desde backend/):
  .venv\\Scripts\\python.exe -m scripts.migrar_ordenes            # dry-run
  .venv\\Scripts\\python.exe -m scripts.migrar_ordenes --apply    # escribe
"""

import argparse
from collections import Counter

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

TOLERANCIA_CIERRE = 0.5
NORMALIZAR_UNIDAD = {"LITROS": "LTS", "KILOS": "KGS", "BOL": "BOLSA", "UN": "UNI"}
LOTE_EXCLUIDO = "PRUE"


def _normalizar(unidad: str | None) -> str:
    if not unidad:
        return "UNI"
    u = unidad.strip().upper()
    return NORMALIZAR_UNIDAD.get(u, u)


def _marker(id_orden: int) -> str:
    return f"Migrado de Orden heredada #{id_orden}"


def _cargar_ordenes(cur) -> list[dict]:
    cur.execute(
        """
        SELECT IdOrden, [Fecha Pedido] AS FechaPedido, [Fecha Ejecucion] AS FechaEjecucion,
               IdTipoLabor, NULLIF(IdContratistaContacto, 0) AS IdContratistaContacto
        FROM dbo.Ordenes
        ORDER BY IdOrden
        """
    )
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _cargar_detalles(cur, id_orden: int) -> list[dict]:
    cur.execute(
        "SELECT IdDetalleOrden, IdFormulado, [Total Aplicado] AS TotalAplicado FROM dbo.Ordenes_Detalles WHERE IdOrden = ? ORDER BY IdDetalleOrden",
        (id_orden,),
    )
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _cargar_distribs(cur, id_detalle: int) -> list[dict]:
    cur.execute(
        """
        SELECT dd.IdDistrib, dd.IdLote, dd.IdCultivo, dd.IdCampaña AS IdCampania, dd.DosisHa,
               dd.CantidadAsignada, dd.Unidad, l.[Numero Lote] AS NumeroLote
        FROM dbo.Ordenes_Detalles_Distrib dd
        JOIN dbo.Lotes l ON l.IdLote = dd.IdLote
        WHERE dd.IdDetalleOrden = ?
        ORDER BY dd.IdDistrib
        """,
        (id_detalle,),
    )
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _aplicar_lote(cur, id_orden: int, id_lote: int, id_cultivo: int, id_campania: int) -> bool:
    cur.execute(
        "SELECT Aplicar FROM dbo.Ordenes_Lotes WHERE IdOrden = ? AND IdLote = ? AND IdCultivo = ? AND IdCampaña = ?",
        (id_orden, id_lote, id_cultivo, id_campania),
    )
    fila = cur.fetchone()
    return bool(fila[0]) if fila else True


def _superficie_lote(cur, id_orden: int, id_lote: int, id_cultivo: int, id_campania: int) -> float | None:
    cur.execute(
        "SELECT Superficie FROM dbo.Ordenes_Lotes WHERE IdOrden = ? AND IdLote = ? AND IdCultivo = ? AND IdCampaña = ?",
        (id_orden, id_lote, id_cultivo, id_campania),
    )
    fila = cur.fetchone()
    return float(fila[0]) if fila and fila[0] is not None else None


def migrar(apply: bool) -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        ordenes = _cargar_ordenes(cur)

        ya_migradas = 0
        sin_tipo_labor = []
        migradas = 0
        insumos_migrados = 0
        distribs_migrados = 0
        revisar_migracion = 0
        unidades_usadas: Counter = Counter()

        for o in ordenes:
            id_orden = o["IdOrden"]
            cur.execute("SELECT 1 FROM dbo.Ordenes_Trabajo WHERE Observaciones = ?", (_marker(id_orden),))
            if cur.fetchone():
                ya_migradas += 1
                continue

            if o["IdTipoLabor"] is None:
                sin_tipo_labor.append(id_orden)
                continue

            estado = "Ejecutada" if o["FechaEjecucion"] is not None else "Planificada"

            id_orden_trabajo = None
            if apply:
                cur.execute(
                    "INSERT INTO dbo.Ordenes_Trabajo (FechaPedido, FechaEjecucion, IdTipoLabor, IdContratistaContacto, Estado, Observaciones) "
                    "OUTPUT INSERTED.IdOrdenTrabajo VALUES (?, ?, ?, ?, ?, ?)",
                    (o["FechaPedido"], o["FechaEjecucion"], o["IdTipoLabor"], o["IdContratistaContacto"], estado, _marker(id_orden)),
                )
                id_orden_trabajo = cur.fetchone()[0]
            migradas += 1

            for d in _cargar_detalles(cur, id_orden):
                distribs = [x for x in _cargar_distribs(cur, d["IdDetalleOrden"]) if x["NumeroLote"] != LOTE_EXCLUIDO]
                if not distribs:
                    continue
                suma = sum(float(x["CantidadAsignada"]) for x in distribs)
                unidades_normalizadas = {_normalizar(x["Unidad"]) for x in distribs}
                for u in unidades_normalizadas:
                    unidades_usadas[u] += 1
                unidad = Counter(_normalizar(x["Unidad"]) for x in distribs).most_common(1)[0][0]
                total_aplicado = d["TotalAplicado"] or 0.0
                revisar = 1 if (abs(suma - total_aplicado) > TOLERANCIA_CIERRE or len(unidades_normalizadas) > 1) else 0
                if revisar:
                    revisar_migracion += 1

                id_orden_insumo = None
                if apply:
                    cur.execute(
                        "INSERT INTO dbo.Ordenes_Trabajo_Insumos (IdOrdenTrabajo, IdProducto, CantidadTotal, Unidad, RevisarMigracion) "
                        "OUTPUT INSERTED.IdOrdenInsumo VALUES (?, ?, ?, ?, ?)",
                        (id_orden_trabajo, d["IdFormulado"], suma, unidad, revisar),
                    )
                    id_orden_insumo = cur.fetchone()[0]
                insumos_migrados += 1

                for x in distribs:
                    superficie = _superficie_lote(cur, id_orden, x["IdLote"], x["IdCultivo"], x["IdCampania"])
                    if superficie is None:
                        superficie = round(float(x["CantidadAsignada"]) / float(x["DosisHa"]), 4) if x["DosisHa"] else 0.0
                    aplicar = _aplicar_lote(cur, id_orden, x["IdLote"], x["IdCultivo"], x["IdCampania"])
                    if apply:
                        cur.execute(
                            "INSERT INTO dbo.Ordenes_Trabajo_Distrib (IdOrdenInsumo, IdLote, IdCultivo, IdCampania, DosisHa, Superficie, CantidadAsignada, Aplicar) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (id_orden_insumo, x["IdLote"], x["IdCultivo"], x["IdCampania"], x["DosisHa"], superficie, x["CantidadAsignada"], 1 if aplicar else 0),
                        )
                    distribs_migrados += 1

        if apply:
            conn.commit()
        else:
            conn.rollback()

        print(f"Modo: {'APLICAR (se escribió en ' + DATABASE + ')' if apply else 'DRY-RUN (solo lectura, nada escrito)'}")
        print(f"Órdenes ya migradas (saltadas, idempotencia): {ya_migradas}")
        print(f"Órdenes migradas: {migradas}")
        print(f"Renglones de insumo migrados: {insumos_migrados}")
        print(f"Distribuciones migradas: {distribs_migrados}")
        print(f"Renglones marcados RevisarMigracion=1: {revisar_migracion}")
        print(f"Unidades normalizadas usadas: {dict(unidades_usadas)}")
        if sin_tipo_labor:
            print(f"ATENCIÓN: {len(sin_tipo_labor)} orden(es) sin IdTipoLabor, no migradas, requieren revisión manual: {sin_tipo_labor}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Escribe la migración. Sin esta bandera corre en modo dry-run (solo lectura).")
    args = parser.parse_args()
    migrar(apply=args.apply)


if __name__ == "__main__":
    main()
