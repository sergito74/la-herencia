"""Migración de datos del módulo Remitos (010-remitos) en `WC`. Idempotente.

1. Rubro «Pérdidas y bajas de insumos» (clasificación Gastos) si no existe.
2. Unidades de medida de los renglones: KG→KGS, PACKS→PACK, Bolsa→BOLSA.
3. Vínculos por documento (`Remitos_Facturas`) que faltan a partir de los vínculos
   por renglón (`tblRemitoCompra`): el vínculo por renglón es la fuente de verdad.
4. Remitos duplicados (mismo proveedor y N°) marcados para revisión. «SIN REMITO» no cuenta:
   es el número que se carga cuando el proveedor entrega sin remito (43 de 215).
5. Unidad base propuesta para cada producto remitido (sin confirmar).

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.migrar_remitos
"""

from collections import Counter, defaultdict

import pyodbc

from src.db.connection import CONNECTION_STRING, DATABASE, _assert_target_is_wc

RUBRO_PERDIDAS = "Pérdidas y bajas de insumos"
NORMALIZAR = {"KG": "KGS", "PACKS": "PACK", "BOLSA": "BOLSA"}


def main() -> None:
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        # 1) Rubro de pérdidas
        cur.execute("SELECT IdRubro FROM dbo.Rubros WHERE Rubro = ?", (RUBRO_PERDIDAS,))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO dbo.Rubros (Rubro, Clasificacion, IdClasifCostoCultivo) VALUES (?, 'Gastos', 5)",
                (RUBRO_PERDIDAS,),
            )
            print(f"Rubro creado: {RUBRO_PERDIDAS}")

        # 2) Unidades
        cambios = 0
        cur.execute("SELECT DISTINCT [Unidad Medida] FROM dbo.Remitos_Detalles")
        for (u,) in cur.fetchall():
            if u is None:
                continue
            nuevo = NORMALIZAR.get(u.strip().upper())
            if nuevo and nuevo != u:
                cur.execute("UPDATE dbo.Remitos_Detalles SET [Unidad Medida] = ? WHERE [Unidad Medida] = ?", (nuevo, u))
                cambios += cur.rowcount
        print(f"Unidades normalizadas: {cambios} renglones")

        # 3) Vínculos por documento
        cur.execute(
            """
            INSERT INTO dbo.Remitos_Facturas (IdRemito, IdDeuda)
            SELECT DISTINCT rd.IdRemito, dc.IdCompra
            FROM dbo.tblRemitoCompra t
            JOIN dbo.Remitos_Detalles rd ON rd.IdDetalleRemito = t.IdDetalleRemito
            JOIN dbo.Det_Compras dc ON dc.IdDetalleCompra = t.IdDetalleCompra
            WHERE NOT EXISTS (SELECT 1 FROM dbo.Remitos_Facturas f WHERE f.IdRemito = rd.IdRemito AND f.IdDeuda = dc.IdCompra)
            """
        )
        print(f"Vínculos por documento agregados: {cur.rowcount}")

        # 4) Duplicados
        cur.execute(
            """
            SELECT r.IdRemito FROM dbo.Remitos r
            JOIN (SELECT IdProveedor, NroRemito FROM dbo.Remitos
                  WHERE UPPER(LTRIM(RTRIM(NroRemito))) <> 'SIN REMITO'
                  GROUP BY IdProveedor, NroRemito HAVING COUNT(*) > 1) d
              ON d.IdProveedor = r.IdProveedor AND d.NroRemito = r.NroRemito
            """
        )
        ids = [r[0] for r in cur.fetchall()]
        for i in ids:
            cur.execute("SELECT 1 FROM dbo.Remitos_Extra WHERE IdRemito = ?", (i,))
            if cur.fetchone():
                cur.execute("UPDATE dbo.Remitos_Extra SET RevisarDuplicado = 1 WHERE IdRemito = ?", (i,))
            else:
                cur.execute("INSERT INTO dbo.Remitos_Extra (IdRemito, RevisarDuplicado) VALUES (?, 1)", (i,))
        print(f"Remitos duplicados marcados para revisión: {len(ids)}")

        # 5) Unidad base propuesta
        cur.execute("SELECT IdFormulado, [Unidad Medida] FROM dbo.Remitos_Detalles WHERE IdFormulado IS NOT NULL")
        usos: dict[int, Counter] = defaultdict(Counter)
        for prod, unidad in cur.fetchall():
            if unidad:
                usos[prod][unidad.strip().upper()] += 1
        cur.execute("SELECT * FROM dbo.vw_CnsU_Producto_link")
        cols = [c[0] for c in cur.description]
        tipo_de = {row[0]: row[4] for row in cur.fetchall()}
        propuestas = 0
        for prod, cnt in usos.items():
            cur.execute("SELECT 1 FROM dbo.Producto_Unidad WHERE IdProducto = ?", (prod,))
            if cur.fetchone():
                continue
            bases = {u: n for u, n in cnt.items() if u in ("LTS", "KGS")}
            if bases:
                base, origen = max(bases, key=bases.get), "uso histórico en remitos"
            else:
                tipo = tipo_de.get(prod)
                base = "KGS" if tipo in ("Fertilizante", "Semilla") else "LTS"
                origen = f"inferida por tipo ({tipo})"
            cur.execute(
                "INSERT INTO dbo.Producto_Unidad (IdProducto, UnidadBase, Confirmada, Origen) VALUES (?, ?, 0, ?)",
                (prod, base, origen),
            )
            propuestas += 1
        print(f"Unidades base propuestas: {propuestas} productos")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(f"OK: migración de remitos aplicada en {DATABASE}.")


if __name__ == "__main__":
    main()
