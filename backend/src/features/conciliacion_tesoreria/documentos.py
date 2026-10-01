"""Documentos y saldo de conciliación compartido (pesos, con signo).

031: lo imputado de Compras, Impuestos y Remuneraciones sale de la fuente
unificada de vínculos (aplicaciones de pago, consumos de tarjeta, cheques,
tesorería y backfill, sin contar dos veces). Antes solo sumaba tesorería
y consumos, y no veía lo aplicado desde Aplicaciones de pago."""

from src.db.connection import fetch_all
from src.formatting import formatear_moneda
from src.features.vinculos import fuente
from src.features.vinculos.cadenas import TIPO_TESORERIA, TOLERANCIA
from src.features.compras.particular import APLICA_PARTICULAR_JOIN
from src.features.remuneraciones.repository import _IMPORTE_SQL

ORIGENES = ("Compras", "Impuestos", "Remuneraciones", "Alquileres")

SQL = f"""
WITH documentos AS (
    SELECT 'Compras' AS origen, CAST(w.IdDeuda AS bigint) AS idOrigen,
        w.Fecha AS fecha, w.[Tipo documento] AS tipoDocumento,
        CAST(w.[Nro Documento] AS nvarchar(255)) AS numeroDocumento,
        w.Moneda AS moneda, w.[Tipo de Cambio] AS tipoDeCambio,
        w.ImporteDocumento-pa.cp AS importeOriginal, w.IdContacto AS idContacto
    FROM dbo.vw_Compras_ImporteDocumento w
    {APLICA_PARTICULAR_JOIN}
    UNION ALL
    SELECT 'Impuestos', i.IdImpuesto, i.Fecha, ti.[Nombre Impuesto],
        CAST(i.[Numero de documento] AS nvarchar(255)), 'Pesos', NULL,
        i.Importe, i.IdOrganismo
    FROM dbo.Impuestos i LEFT JOIN dbo.[Tipo Impuesto] ti ON ti.IdTipoImpuesto=i.IdTipoImpuesto
    UNION ALL
    SELECT 'Remuneraciones', r.IdSalario, r.[Fecha de pago], 'Liquidación',
        CAST(r.[Periodo liquidado] AS nvarchar(255)), 'Pesos', NULL,
        ({_IMPORTE_SQL}), r.IdContacto FROM dbo.Remuneraciones r
    UNION ALL
    SELECT 'Alquileres', d.IdCobroAlquiler, d.[Fecha vencimiento], 'Cuota alquiler',
        CONCAT(a.IdAlquiler, '/', d.[Numero Cuota]), 'Pesos', NULL,
        d.[Importe Cuota], a.IdContacto
    FROM dbo.[Detalle Cobro Alquiler] d JOIN dbo.Alquileres a ON a.IdAlquiler=d.IdAlquiler
), pagos AS (
    SELECT TipoOrigenDocumento AS origen, IdOrigenDocumento AS idOrigen, Importe AS importe
    FROM dbo.ConciliacionesTesoreria WHERE TipoOrigenDocumento IS NOT NULL
    UNION ALL
    SELECT CASE WHEN IdCompra IS NOT NULL THEN 'Compras' ELSE 'Impuestos' END,
        COALESCE(IdCompra,IdImpuesto), ImporteImputado
    FROM dbo.Tarjetas_Resumenes_Lineas_Compras
), totales AS (
    SELECT origen,idOrigen,SUM(importe) AS imputado,COUNT(*) AS vinculosPrevios
    FROM pagos GROUP BY origen,idOrigen
), pesos AS (
    SELECT d.*, c.[Razon Social] AS contraparte,
        CASE WHEN d.moneda='Dolares' THEN
            CASE WHEN d.tipoDeCambio>0 THEN ROUND(ROUND(d.importeOriginal,2)*d.tipoDeCambio,2) ELSE NULL END
            ELSE ROUND(d.importeOriginal,2) END AS importePesos,
        ISNULL(t.imputado,0) AS imputado,ISNULL(t.vinculosPrevios,0) AS vinculosPrevios
    FROM documentos d LEFT JOIN totales t ON t.origen=d.origen AND t.idOrigen=d.idOrigen
    LEFT JOIN dbo.Contactos c ON c.IdContacto=d.idContacto
), saldos AS (
    SELECT *, CASE WHEN importePesos>0 THEN
        CASE WHEN importePesos-imputado>0 THEN ROUND(importePesos-imputado,2) ELSE 0 END
        ELSE CASE WHEN importePesos-imputado<0 THEN ROUND(importePesos-imputado,2) ELSE 0 END
        END AS saldoPendiente
    FROM pesos
)
"""


def _unificar(rows: list[dict]) -> list[dict]:
    claves = [(TIPO_TESORERIA[r["origen"]], r["idOrigen"]) for r in rows if r["origen"] in TIPO_TESORERIA]
    if not claves:
        return rows
    pagado = fuente.pagado_de_documentos(claves)
    for r in rows:
        if r["origen"] not in TIPO_TESORERIA:
            continue
        r["imputado"] = pagado[(TIPO_TESORERIA[r["origen"]], r["idOrigen"])]
        total = r["importePesos"]
        if total is None:
            continue
        resto = round(float(total) - r["imputado"], 2)
        r["saldoPendiente"] = max(resto, 0.0) if total > 0 else min(resto, 0.0)
    return rows


def buscar(texto: str, *, importe: float | None = None, fecha=None) -> list[dict]:
    if importe is None and not 2 <= len(texto.strip()) <= 100:
        raise ValueError("La búsqueda debe tener entre 2 y 100 caracteres.")
    base = (
        SQL
        + "SELECT TOP (?) * FROM saldos WHERE idContacto IS NOT NULL AND importePesos IS NOT NULL AND ABS(saldoPendiente)>=0.005"
    )
    if importe is None:
        return _unificar(fetch_all(
            base
            + " AND (contraparte LIKE ? OR numeroDocumento LIKE ?) ORDER BY fecha DESC,origen,idOrigen",
            (40, f"%{texto.strip()}%", f"%{texto.strip()}%"),
        ))
    return _unificar(fetch_all(
        base
        + " ORDER BY CASE WHEN ABS(saldoPendiente-?)<=0.10 THEN 0 ELSE 1 END, ABS(DATEDIFF(day,fecha,?)),ABS(saldoPendiente-?),origen,idOrigen",
        (60, importe, fecha, importe),
    ))


def por_referencias(refs: list[dict]) -> list[dict]:
    if not 1 <= len(refs) <= 20:
        raise ValueError("Elegí de 1 a 20 documentos.")
    keys = [(r["origen"], r["idOrigen"]) for r in refs]
    if len(set(keys)) != len(keys) or any(o not in ORIGENES or not -(2**63) <= i < 2**63 for o, i in keys):
        raise ValueError("Referencias documentales inválidas o repetidas.")
    where = " OR ".join("(origen=? AND idOrigen=?)" for _ in refs)
    rows = _unificar(fetch_all(
        SQL + "SELECT * FROM saldos WHERE " + where, tuple(v for key in keys for v in key)
    ))
    by_key = {(r["origen"], r["idOrigen"]): r for r in rows}
    if any(key not in by_key for key in keys):
        raise LookupError("No existe uno de los documentos elegidos.")
    return [by_key[key] for key in keys]


def saldo_documento(origen: str, id_origen: int) -> float:
    row = por_referencias([dict(origen=origen, idOrigen=id_origen)])[0]
    if row["importePesos"] is None:
        raise ValueError("El documento en dólares no tiene tipo de cambio válido.")
    return float(row["saldoPendiente"])


def validar_imputacion(saldo: float, importe: float) -> str | None:
    """031 (FR-012): un exceso de más del 2% sobre el saldo del documento
    (contando todas las vías) se rechaza; dentro del 2% se permite y se
    devuelve una advertencia."""
    if importe == 0 or (saldo != 0 and saldo * importe < 0):
        raise ValueError("El importe tiene otro signo que el saldo del documento.")
    exceso = abs(importe) - abs(saldo)
    if exceso <= 0.01:
        return None
    if exceso > max(1.0, abs(importe) * TOLERANCIA):
        raise ValueError(
            f"El importe excede el saldo documental compartido ({formatear_moneda(abs(saldo))}) en "
            f"{formatear_moneda(exceso)}, más del 2% permitido."
        )
    return f"El documento queda imputado {formatear_moneda(exceso)} por encima de su total (dentro del 2% de tolerancia)."


def totales_imputados(refs: list[tuple[str, int]]) -> dict[tuple[str, int], float]:
    """Lectura agrupada para listados de Tarjetas; evita una consulta por fila."""
    result = {}
    refs = list(dict.fromkeys(refs))
    for start in range(0, len(refs), 100):
        chunk = refs[start : start + 100]
        where = " OR ".join("(origen=? AND idOrigen=?)" for _ in chunk)
        rows = fetch_all(
            """WITH pagos AS (
            SELECT TipoOrigenDocumento AS origen, IdOrigenDocumento AS idOrigen, Importe AS importe
            FROM dbo.ConciliacionesTesoreria WHERE TipoOrigenDocumento IS NOT NULL
            UNION ALL
            SELECT CASE WHEN IdCompra IS NOT NULL THEN 'Compras' ELSE 'Impuestos' END,
                COALESCE(IdCompra,IdImpuesto),ImporteImputado
            FROM dbo.Tarjetas_Resumenes_Lineas_Compras)
            SELECT origen,idOrigen,SUM(importe) AS total FROM pagos WHERE """
            + where
            + " GROUP BY origen,idOrigen",
            tuple(v for ref in chunk for v in ref),
        )
        result.update({(r["origen"], r["idOrigen"]): float(r["total"]) for r in rows})
    return result
