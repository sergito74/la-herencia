"""Sugerencia de producto del catálogo a partir del texto del renglón de factura (050, 16/11/2026).

Misma lógica validada en la simulación (scripts/simulacion_kardex_corte_050.py): mismo texto ya cargado, texto
parecido, marca comercial, código de la marca o palabra única de una marca.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from src.db.connection import fetch_all
from src.features.imputacion.aprendizaje import tokens
from src.features.imputacion.tamiz import normalizar

# Vías con las que se asigna el producto sin preguntar (las demás quedan como sugerencia para revisar).
SEGURAS = ("mismo texto", "marca comercial", "código de marca", "familia de fertilizante")


def _palabras(t: str) -> frozenset:
    """Palabras del texto normalizado conservando códigos con números (3970, 46R18), sin conectores ni unidades."""
    ruido = {"DE", "DEL", "LA", "EL", "Y", "X", "KG", "KGS", "LTS", "LT", "L", "LITROS", "BOLSA", "BOLSAS", "BIG", "BAG",
             "GRANEL", "TRAT", "C", "B1", "B2", "SEMILLA", "SEMILLAS"}
    return frozenset(w for w in re.split(r"[^A-Z0-9]+", t) if len(w) >= 2 and w not in ruido)


class Sugeridor:
    def __init__(self):
        self.exacto: dict[str, Counter] = defaultdict(Counter)
        self.toks: dict[str, frozenset] = {}
        for f in fetch_all("SELECT [Producto/Servicio] t, IdFormulado p FROM dbo.Det_Compras WHERE IdFormulado > 0"):
            t = normalizar(f["t"])
            self.exacto[t][f["p"]] += 1
            self.toks.setdefault(t, tokens(t))
        # Fitosanitarios, semillas y fertilizantes (vw_ProductosBase) usados en órdenes o recuentos.
        usados = fetch_all(
            """SELECT DISTINCT CAST(v.IdProducto AS bigint) p, v.Producto m FROM dbo.vw_ProductosBase v
               WHERE v.IdProducto IN (SELECT IdProducto FROM dbo.Ordenes_Trabajo_Insumos UNION SELECT IdFormulado FROM dbo.Ordenes_Detalles
                                      UNION SELECT IdProducto FROM dbo.Stock_Recuentos_Detalle)""")
        self.marcas = [(_palabras(normalizar(u["m"])), u["p"]) for u in usados if u["m"]]
        # Semillas de todo el catálogo (una variedad nueva todavía no está en órdenes ni recuentos): solo por código.
        self.semillas = [(_palabras(normalizar(u["m"])), u["p"]) for u in fetch_all(
            "SELECT CAST(IdProducto AS bigint) p, Producto m FROM dbo.vw_ProductosBase WHERE TipoProducto = 'Semilla' AND IdProducto IS NOT NULL") if u["m"]]
        # Fertilizante por familia (arrancador / urea): el producto de esa familia más usado en órdenes.
        from collections import Counter as _C
        from src.features.remitos.vinculo_auto import familia_fertilizante
        uso = _C(int(f["p"]) for f in fetch_all("SELECT IdProducto p FROM dbo.Ordenes_Trabajo_Insumos"))
        self.familias: dict[str, int] = {}
        for f in fetch_all("SELECT CAST(IdProducto AS bigint) p, Producto m FROM dbo.vw_ProductosBase WHERE TipoProducto = 'Fertilizante' AND IdProducto IS NOT NULL"):
            fam = familia_fertilizante(f["m"])
            if fam and (fam not in self.familias or uso[int(f["p"])] > uso[self.familias[fam]]):
                self.familias[fam] = int(f["p"])

    def sugerir(self, texto) -> tuple[int | None, str]:
        t = normalizar(texto)
        if self.exacto.get(t):
            return self.exacto[t].most_common(1)[0][0], "mismo texto"
        mios = tokens(t)
        mejor, pid = 0.0, None
        for otro, tk in self.toks.items():
            if tk and mios:
                s = len(mios & tk) / len(mios | tk)
                if s > mejor:
                    mejor, pid = s, self.exacto[otro].most_common(1)[0][0]
        if mejor >= 0.6:
            return pid, "texto parecido"
        mis = _palabras(t)
        mejor_m = (0.0, 0, None)
        for m, p in self.marcas:
            if not m:
                continue
            s = len(m & mis) / len(m)
            # "SYN 3970" = "SYN 3970 CL": todo el texto (con su código numérico) está dentro de la marca.
            todo = len(m & mis) >= 2 and mis <= m and any(ch.isdigit() for w in mis for ch in w)
            if (s >= 0.67 or todo) and len(m & mis) >= 1 and (s, len(m), p) > mejor_m:
                mejor_m = (s, len(m), p)
        if mejor_m[2]:
            return int(mejor_m[2]), "marca comercial"
        # Código de la marca escrito distinto ("SOJA DM 46 R 18" = DON MARIO 46R18, "MAIZ LT 725 TRE" = LT725TRE), o una
        # palabra distintiva que solo tiene una marca (Rinder = DIFLU 50 RINDER).
        compacto = re.sub(r"[^A-Z0-9]", "", t)
        cand = set()
        for m, p in self.marcas:
            cod = [w for w in m if any(ch.isdigit() for ch in w) and len(w) >= 4]
            if cod and all(w in compacto for w in cod) and len(re.sub(r"\D", "", "".join(cod))) >= 3:
                cand.add(int(p))
        if len(cand) == 1:
            return cand.pop(), "código de marca"
        if not cand:
            for m, p in self.semillas:
                cod = [w for w in m if any(ch.isdigit() for ch in w) and len(w) >= 5]
                if cod and all(w in compacto for w in cod):
                    cand.add(int(p))
            if len(cand) == 1:
                return cand.pop(), "código de marca"
        from src.features.remitos.vinculo_auto import familia_fertilizante
        fam = familia_fertilizante(t)
        if fam and fam in self.familias:
            return self.familias[fam], "familia de fertilizante"
        if not hasattr(self, "_unicas"):
            cuenta = Counter(w for m, _ in self.marcas for w in m)
            self._unicas = {w: int(p) for m, p in self.marcas for w in m if cuenta[w] == 1 and len(w) >= 5 and w.isalpha()}
        hits = {self._unicas[w] for w in mis if w in self._unicas}
        if len(hits) == 1:
            return hits.pop(), "palabra única de marca"
        return None, "sin sugerencia"
