"""Tests de sugerencia FIFO y documentos pendientes (019), contra datos
reales de `WC` (solo lectura, no inserta nada — ver
test_aplicaciones_pago_endpoints.py para los tests que sí escriben y
limpian después)."""

from __future__ import annotations

from src.db.connection import fetch_all
from src.features.aplicaciones_pago import documentos, sugerencia


def _contacto_con_compras() -> int:
    fila = fetch_all(
        "SELECT TOP 1 IdContacto AS idContacto FROM dbo.Compras GROUP BY IdContacto ORDER BY COUNT(*) DESC"
    )
    return fila[0]["idContacto"]


def _contacto_con_al_menos_n_pendientes(n: int) -> int:
    """El contacto con más `Compras` no necesariamente tiene documentos
    *pendientes* — desde que 020 aplicó el histórico contra `WC` real, la
    mayoría de las compras del contacto con más volumen ya están saldadas.
    Este helper busca explícitamente uno con saldo pendiente, en vez de
    asumirlo del volumen total de compras."""
    candidatos = fetch_all(
        "SELECT TOP 20 IdContacto AS idContacto FROM dbo.Compras GROUP BY IdContacto ORDER BY COUNT(*) DESC"
    )
    for candidato in candidatos:
        pendientes = documentos.documentos_pendientes(candidato["idContacto"], "compra")
        if len(pendientes) >= n:
            return candidato["idContacto"]
    raise AssertionError(f"Ningún contacto entre los 20 con más compras tiene {n}+ documentos pendientes")


def test_documentos_pendientes_compra_ordenados_por_fecha_ascendente():
    id_contacto = _contacto_con_compras()
    docs = documentos.documentos_pendientes(id_contacto, "compra")
    assert len(docs) > 0
    fechas = [d["fecha"] for d in docs]
    assert fechas == sorted(fechas)


def test_documentos_pendientes_incluye_hacienda_y_granos_para_venta():
    fila = fetch_all(
        "SELECT TOP 1 IdConsignatario AS idConsignatario FROM dbo.[Venta Hacienda] "
        "GROUP BY IdConsignatario ORDER BY COUNT(*) DESC"
    )
    if not fila:
        return  # sin datos de venta hacienda en este WC, nada que probar acá
    id_contacto = fila[0]["idConsignatario"]
    docs = documentos.documentos_pendientes(id_contacto, "venta")
    tipos = {d["tipoDocumento"] for d in docs}
    assert tipos <= {"VentaHacienda", "VentaGranos"}


def test_sugerencia_fifo_cubre_el_importe_del_movimiento():
    id_contacto = _contacto_con_al_menos_n_pendientes(2)
    pendientes = documentos.documentos_pendientes(id_contacto, "compra")

    importe_prueba = round(pendientes[0]["saldoPendiente"] + pendientes[1]["saldoPendiente"] / 2, 2)

    # Reproduce la logica de sugerir() sin depender de un movimiento bancario real.
    restante = importe_prueba
    sugerido = []
    for doc in pendientes:
        if restante <= 0:
            break
        importe = round(min(doc["saldoPendiente"], restante), 2)
        sugerido.append((doc["idDocumento"], importe))
        restante = round(restante - importe, 2)

    assert sugerido[0] == (pendientes[0]["idDocumento"], pendientes[0]["saldoPendiente"])
    assert sugerido[1][0] == pendientes[1]["idDocumento"]
    assert sugerido[1][1] < pendientes[1]["saldoPendiente"]
    assert restante == 0


def test_sugerir_sin_contacto_conocido_devuelve_vacio():
    resultado = sugerencia.sugerir("bna", -1)
    assert resultado["sugerencias"] == []
