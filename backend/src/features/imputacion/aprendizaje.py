"""Aprendizaje de la imputación histórica (050, pedido de Sergio 14/11/2026).

"El centro de costos se define según el destino que se le dio a esa compra; hay que aprender de la historia".
La historia muestra dos señales fuertes y se usan solo esas (nunca el proveedor, P10):

1. El cultivo decide el centro: Sorgo, Avena, Pastura, Maíz diferido → Ganadería (forrajeros); Soja,
   Maíz, Trigo, Girasol → Agricultura (≈98% de los renglones).
2. Sin cultivo, el texto del renglón dentro de su rubro decide (Honorarios "certificación balance" →
   Adm. General; "sangrado brucelosis" → Ganadería). Si el texto no aparece, el más parecido; si tampoco,
   lo habitual del rubro.

`Modelo` se arma con los renglones imputados desde el 01/09/2015. Para la simulación histórica se usa en modo
incremental (`observar` después de `predecir`), así cada renglón se predice solo con la historia anterior.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache

from src.db.connection import fetch_all

NO_APLICA = 20
CENTRO_GANADERIA = 2
CENTROS_ESTRUCTURA = (3, 4, 5)  # Adm. General, Maquinaria, SIP
MIN_SOPORTE_CULTIVO = 5
COINCIDENCIA_TEXTO = 0.8
SIMILITUD_MINIMA = 0.5
HABITUAL_RUBRO = 0.6
# Sin historia del texto (primeras veces): palabras inequívocas de hacienda → Ganadería.
HACIENDA = ("TORO", "VACA", "VAQUILL", "NOVILL", "TERNER", "HACIENDA", "RODEO", "AFTOSA", "BRUCEL", "VACUN",
            "SENASA", "GUIA", "TACTO", "SANGRADO", "BOYERO", "JERINGA", "MANGA", "BRETE", "BEBEDERO", "PASTAJE",
            "FEED LOT", "FEEDLOT", "DESPARASIT", "INSEMIN")
_RUIDO = {"DE", "DEL", "LA", "EL", "Y", "POR", "X", "EN", "A", "CON", "PARA", "LOS", "LAS", "N", "NRO", "FC", "FACT"}


def tokens(texto_normalizado: str) -> frozenset[str]:
    """Palabras significativas (sin números sueltos ni conectores) del texto ya normalizado."""
    return frozenset(t for t in re.split(r"[^A-Z0-9]+", texto_normalizado)
                     if len(t) >= 3 and not t.isdigit() and t not in _RUIDO)


def categoria_manual(id_cultivo: int | None, id_campania: int | None, id_centro: int | None) -> str:
    """Cómo quedó imputado a mano: Cultivo / Ganaderia / Estructura."""
    if id_cultivo and id_campania and id_campania != NO_APLICA:
        return "Cultivo"
    if id_centro == CENTRO_GANADERIA:
        return "Ganaderia"
    return "Estructura"


@dataclass
class Prediccion:
    destino: str          # Ganaderia | Estructura
    centro: int | None
    confianza: float
    base: str             # "texto", "texto parecido", "rubro"


@dataclass
class Modelo:
    centro_cultivo: dict[int, Counter] = field(default_factory=lambda: defaultdict(Counter))
    por_texto: dict[tuple, Counter] = field(default_factory=lambda: defaultdict(Counter))
    por_rubro: dict[int, Counter] = field(default_factory=lambda: defaultdict(Counter))
    textos_rubro: dict[int, dict] = field(default_factory=lambda: defaultdict(dict))

    def observar(self, id_rubro, texto: str, id_cultivo, id_campania, id_centro) -> None:
        if id_cultivo and id_centro:
            self.centro_cultivo[id_cultivo][id_centro] += 1
        cat = categoria_manual(id_cultivo, id_campania, id_centro)
        if cat == "Cultivo" or id_rubro is None:
            return
        clave = (cat, id_centro)
        self.por_texto[(id_rubro, texto)][clave] += 1
        self.por_rubro[id_rubro][clave] += 1
        self.textos_rubro[id_rubro].setdefault(texto, tokens(texto))

    def centro_de_cultivo(self, id_cultivo: int | None) -> int | None:
        c = self.centro_cultivo.get(id_cultivo)
        if not c or sum(c.values()) < MIN_SOPORTE_CULTIVO:
            return None
        return c.most_common(1)[0][0]

    @staticmethod
    def _mayoria(c: Counter) -> tuple[tuple, float]:
        clave, n = c.most_common(1)[0]
        return clave, n / sum(c.values())

    def predecir(self, id_rubro, texto: str) -> Prediccion | None:
        """Destino fuera de cultivo (Ganadería / Estructura) para un renglón sin cultivo."""
        exacto = self.por_texto.get((id_rubro, texto))
        if exacto:
            (cat, centro), conf = self._mayoria(exacto)
            if conf >= COINCIDENCIA_TEXTO:
                return Prediccion(cat, centro, conf, "texto")
        mios = tokens(texto)
        if mios and self.textos_rubro.get(id_rubro):
            parecidos = Counter()
            mejor = 0.0
            for otro, toks in self.textos_rubro[id_rubro].items():
                if not toks:
                    continue
                sim = len(mios & toks) / len(mios | toks)
                if sim >= SIMILITUD_MINIMA:
                    mejor = max(mejor, sim)
                    parecidos.update(self.por_texto[(id_rubro, otro)])
            if parecidos:
                (cat, centro), conf = self._mayoria(parecidos)
                if conf >= COINCIDENCIA_TEXTO:
                    return Prediccion(cat, centro, conf * mejor, "texto parecido")
        if not exacto and any(p in texto for p in HACIENDA):
            return Prediccion("Ganaderia", CENTRO_GANADERIA, 0.9, "palabra de hacienda")
        rub = self.por_rubro.get(id_rubro)
        if rub:
            (cat, centro), conf = self._mayoria(rub)
            if conf >= HABITUAL_RUBRO:
                return Prediccion(cat, centro, conf, "rubro")
        return None


def filas_historicas() -> list[dict]:
    return fetch_all(
        """
        SELECT d.IdDetalleCompra AS id, c.Fecha AS fecha, d.IdRubro AS idRubro, d.[Producto/Servicio] AS producto,
               de.IdCultivo AS idCultivo, d.[IdCampaña] AS idCampania, d.IdCentroCostos AS idCentro
        FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        LEFT JOIN dbo.DestinoCompras de ON de.IdDestino = d.IdDestino
        WHERE c.Fecha >= '2015-09-01'
          AND NOT EXISTS (SELECT 1 FROM dbo.TamizRenglones tz WHERE tz.IdDetalleCompra = d.IdDetalleCompra AND tz.Vigente = 1)
        ORDER BY c.Fecha, d.IdDetalleCompra
        """
    )


@lru_cache(maxsize=1)
def modelo() -> Modelo:
    """Modelo con toda la historia imputada a mano (la caché se renueva al reiniciar o con `modelo.cache_clear()`)."""
    from src.features.imputacion.tamiz import normalizar

    m = Modelo()
    for f in filas_historicas():
        m.observar(f["idRubro"], normalizar(f["producto"]), f["idCultivo"], f["idCampania"], f["idCentro"])
    return m
