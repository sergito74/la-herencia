"""Traducción entre claves heredadas: Cultivo → IdDestino/IdGrano
(`Map_CultivoResultado`) y Campaña texto ↔ IdCampaña (`Campañas`).

`Map_CultivoResultado` es 1:1 por Cultivo (verificado contra `WC`, 11 filas,
research.md §3) — nunca hay más de un Destino o Grano por Cultivo. Las vistas
de costeo (`vw_ResultadosCultivo_CostosBase`/`Seguros`) usan `IdDestino`; las
de venta (`vw_ResultadosCultivo_Ventas`/`Deducciones`) usan `IdGrano` para
llegar al Cultivo, pero filtran por `Campaña` como texto, no por `IdCampaña`
— de ahí que haga falta traducir la Campaña en ambos sentidos (research.md §4).
"""

from __future__ import annotations

from src.db.connection import fetch_one


def idCultivo_a_destino(id_cultivo: int) -> int | None:
    fila = fetch_one("SELECT IdDestino FROM dbo.Map_CultivoResultado WHERE IdCultivo = ?", (id_cultivo,))
    return fila["IdDestino"] if fila else None


def idCultivo_a_grano(id_cultivo: int) -> int | None:
    fila = fetch_one("SELECT IdGrano FROM dbo.Map_CultivoResultado WHERE IdCultivo = ?", (id_cultivo,))
    return fila["IdGrano"] if fila else None


def campania_texto_a_id(texto: str) -> int | None:
    fila = fetch_one("SELECT IdCampaña AS id FROM dbo.Campañas WHERE Campaña = ?", (texto,))
    return fila["id"] if fila else None


def campania_id_a_texto(id_campania: int) -> str | None:
    fila = fetch_one("SELECT Campaña AS texto FROM dbo.Campañas WHERE IdCampaña = ?", (id_campania,))
    return fila["texto"] if fila else None
