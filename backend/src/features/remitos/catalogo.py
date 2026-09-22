"""Catálogo de insumos y unidades de medida (agroquímicos, fertilizantes y semillas).

Los productos vienen del catálogo unificado heredado (`vw_ProductosBase`, 9.516
productos). Cada producto tiene una **unidad base** (litros, kilos o unidades) y,
si se remita en presentaciones (bolsa, bidón, pack…), su equivalencia a la base.
"""

from __future__ import annotations

from src.db.connection import execute_write, execute_write_transaction, fetch_all, fetch_one


def listar_unidades() -> list[dict]:
    return fetch_all(
        "SELECT Codigo AS codigo, Nombre AS nombre, Magnitud AS magnitud, EsBase AS esBase FROM dbo.Unidades_Medida ORDER BY Orden"
    )


def _es_base(unidad: str) -> bool:
    fila = fetch_one("SELECT EsBase AS esBase FROM dbo.Unidades_Medida WHERE Codigo = ?", (unidad,))
    return bool(fila and fila["esBase"])


def existe_unidad(unidad: str) -> bool:
    return fetch_one("SELECT 1 AS x FROM dbo.Unidades_Medida WHERE Codigo = ?", (unidad,)) is not None


def existe_producto(id_producto: int) -> bool:
    return fetch_one("SELECT 1 AS x FROM dbo.vw_ProductosBase WHERE IdProducto = ?", (id_producto,)) is not None


_SELECT_PRODUCTO = """
    SELECT CAST(p.IdProducto AS int) AS idProducto, p.Producto AS producto, p.TipoProducto AS tipo, p.IngredienteActivo AS ingredienteActivo,
           u.UnidadBase AS unidadBase, u.Confirmada AS unidadConfirmada, u.Origen AS unidadOrigen
    FROM dbo.vw_ProductosBase p
    LEFT JOIN dbo.Producto_Unidad u ON u.IdProducto = p.IdProducto
"""


def buscar_productos(q: str | None = None, tipo: str | None = None, limite: int = 30) -> list[dict]:
    """Búsqueda por nombre, principio activo o tipo. Prioriza los que ya tienen unidad
    base (los que ya se usan en remitos) y los nombres que empiezan con el texto."""
    condiciones, params = ["1 = 1"], []
    if q and q.strip():
        condiciones.append("(p.Producto LIKE ? OR p.IngredienteActivo LIKE ?)")
        params += [f"%{q.strip()}%", f"%{q.strip()}%"]
    if tipo:
        condiciones.append("p.TipoProducto = ?")
        params.append(tipo)
    orden_q = q.strip() if q and q.strip() else ""
    filas = fetch_all(
        f"""
        SELECT TOP (?) x.* FROM ({_SELECT_PRODUCTO} WHERE {' AND '.join(condiciones)}) x
        ORDER BY CASE WHEN x.unidadBase IS NULL THEN 1 ELSE 0 END,
                 CASE WHEN x.producto LIKE ? THEN 0 ELSE 1 END, x.producto
        """,
        (limite, *params, f"{orden_q}%"),
    )
    return filas


def get_producto(id_producto: int) -> dict | None:
    fila = fetch_one(f"{_SELECT_PRODUCTO} WHERE p.IdProducto = ?", (id_producto,))
    if fila is None:
        return None
    fila["equivalencias"] = fetch_all(
        "SELECT Unidad AS unidad, FactorABase AS factor FROM dbo.Producto_Equivalencias WHERE IdProducto = ? ORDER BY Unidad",
        (id_producto,),
    )
    return fila


def tipos_de_producto() -> list[str]:
    return [r["t"] for r in fetch_all("SELECT DISTINCT TipoProducto AS t FROM dbo.vw_ProductosBase WHERE TipoProducto IS NOT NULL ORDER BY 1")]


def unidad_base_sugerida(tipo: str | None) -> str:
    return "KGS" if tipo in ("Fertilizante", "Semilla") else "LTS"


def tiene_movimientos(id_producto: int) -> bool:
    return (
        fetch_one("SELECT TOP 1 1 AS x FROM dbo.Remitos_Detalles WHERE IdFormulado = ?", (id_producto,)) is not None
        or fetch_one("SELECT TOP 1 1 AS x FROM dbo.Stock_Ajustes WHERE IdProducto = ?", (id_producto,)) is not None
    )


def stmt_unidad_base(id_producto: int, unidad: str, confirmada: bool, origen: str) -> list:
    """Sentencias para dejar la unidad base de un producto (alta o cambio)."""
    existente = fetch_one("SELECT 1 AS x FROM dbo.Producto_Unidad WHERE IdProducto = ?", (id_producto,))
    if existente:
        return [("UPDATE dbo.Producto_Unidad SET UnidadBase = ?, Confirmada = ?, Origen = ? WHERE IdProducto = ?", (unidad, 1 if confirmada else 0, origen, id_producto))]
    return [("INSERT INTO dbo.Producto_Unidad (IdProducto, UnidadBase, Confirmada, Origen) VALUES (?, ?, ?, ?)", (id_producto, unidad, 1 if confirmada else 0, origen))]


def stmt_equivalencia(id_producto: int, unidad: str, factor: float) -> list:
    existente = fetch_one("SELECT 1 AS x FROM dbo.Producto_Equivalencias WHERE IdProducto = ? AND Unidad = ?", (id_producto, unidad))
    if existente:
        return [("UPDATE dbo.Producto_Equivalencias SET FactorABase = ? WHERE IdProducto = ? AND Unidad = ?", (factor, id_producto, unidad))]
    return [("INSERT INTO dbo.Producto_Equivalencias (IdProducto, Unidad, FactorABase) VALUES (?, ?, ?)", (id_producto, unidad, factor))]


def set_unidad_base(id_producto: int, unidad: str) -> None:
    if not existe_producto(id_producto):
        raise ValueError([f"El producto {id_producto} no existe."])
    if not _es_base(unidad):
        raise ValueError([f"«{unidad}» no es una unidad base (usá litros, kilos o unidades)."])
    actual = fetch_one("SELECT UnidadBase AS u, Confirmada AS c FROM dbo.Producto_Unidad WHERE IdProducto = ?", (id_producto,))
    if actual and actual["c"] and actual["u"] != unidad and tiene_movimientos(id_producto):
        raise ValueError(["La unidad base ya está confirmada y el producto tiene movimientos: no se puede cambiar sin descuadrar el stock."])
    execute_write_transaction(stmt_unidad_base(id_producto, unidad, True, "confirmada por el usuario"))


def set_equivalencia(id_producto: int, unidad: str, factor: float) -> None:
    if not existe_producto(id_producto):
        raise ValueError([f"El producto {id_producto} no existe."])
    if not existe_unidad(unidad) or _es_base(unidad):
        raise ValueError([f"«{unidad}» no es una presentación (bolsa, bidón, pack…)."])
    if not factor or factor <= 0:
        raise ValueError(["La equivalencia debe ser mayor a cero."])
    execute_write_transaction(stmt_equivalencia(id_producto, unidad, factor))


def productos_por_confirmar() -> list[dict]:
    """Productos con unidad base propuesta (uso histórico) y todavía sin confirmar."""
    return fetch_all(
        """
        SELECT CAST(p.IdProducto AS int) AS idProducto, p.Producto AS producto, p.TipoProducto AS tipo, u.UnidadBase AS unidadBase, u.Origen AS origen,
               (SELECT COUNT(*) FROM dbo.Remitos_Detalles rd WHERE rd.IdFormulado = p.IdProducto) AS renglones
        FROM dbo.Producto_Unidad u JOIN dbo.vw_ProductosBase p ON p.IdProducto = u.IdProducto
        WHERE u.Confirmada = 0 ORDER BY p.Producto
        """
    )


def confirmar_unidades(ids: list[int]) -> int:
    if not ids:
        return 0
    marcas = ",".join("?" for _ in ids)
    return execute_write(f"UPDATE dbo.Producto_Unidad SET Confirmada = 1, Origen = 'confirmada por el usuario' WHERE IdProducto IN ({marcas}) AND Confirmada = 0", tuple(ids))
