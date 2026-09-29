"""One-off: reemplaza el `Detalle` de líneas de resumen de tarjeta AgroNacion
que quedaron con el `IdContacto` pegado como texto (bug de carga histórica,
2013-2023) por la Razón Social del contacto. Re-corrible: solo toca filas
donde `Detalle = CAST(IdContacto AS VARCHAR)`, así que una vez corregidas
dejan de matchear y una segunda corrida no hace nada.
"""

from src.db.connection import execute_write, fetch_all


def main() -> None:
    filas = fetch_all(
        "SELECT l.IdLineaConsumo AS id, c.[Razon Social] AS razonSocial "
        "FROM dbo.Tarjetas_Resumenes_Lineas l "
        "JOIN dbo.Contactos c ON c.IdContacto = l.IdContacto "
        "WHERE l.Detalle = CAST(l.IdContacto AS VARCHAR)"
    )
    print(f"{len(filas)} líneas a corregir")
    total = 0
    for fila in filas:
        total += execute_write(
            "UPDATE dbo.Tarjetas_Resumenes_Lineas SET Detalle = ? WHERE IdLineaConsumo = ?",
            (fila["razonSocial"], fila["id"]),
        )
    print(f"{total} filas actualizadas")


if __name__ == "__main__":
    main()
