"""Habilita Bolsa, Pack y Kit como unidades base seleccionables en `Unidades_Medida`.

`Unidades_Medida.EsBase` filtra qué unidades aparecen en el selector de
"Unidad base" de `/produccion/stock/unidades` — BOLSA y PACK ya existían pero
con `EsBase=0` (pensadas solo como unidad de remito, no de stock); KIT no
existía. Pedido del usuario 2026-09-22: los tres deben poder elegirse como
unidad base de un producto. Idempotente.

Uso (desde backend/):  .venv\\Scripts\\python.exe -m scripts.habilitar_unidades_bolsa_pack_kit
"""

from src.db.connection import execute_write, fetch_all, fetch_one

CODIGOS_A_HABILITAR = ("BOLSA", "PACK")


def main() -> None:
    for codigo in CODIGOS_A_HABILITAR:
        n = execute_write("UPDATE dbo.Unidades_Medida SET EsBase = 1 WHERE Codigo = ? AND EsBase = 0", (codigo,))
        print(f"{codigo}: EsBase actualizado ({n} fila(s))." if n else f"{codigo}: ya era EsBase=1, sin cambios.")

    if fetch_one("SELECT 1 AS x FROM dbo.Unidades_Medida WHERE Codigo = 'KIT'"):
        print("KIT: ya existe, sin cambios.")
    else:
        orden = fetch_all("SELECT MAX(Orden) AS m FROM dbo.Unidades_Medida")[0]["m"] or 0
        execute_write(
            "INSERT INTO dbo.Unidades_Medida (Codigo, Nombre, Magnitud, EsBase, Orden) VALUES (?, ?, ?, 1, ?)",
            ("KIT", "Kit", None, orden + 1),
        )
        print("KIT: creado con EsBase=1.")


if __name__ == "__main__":
    main()
