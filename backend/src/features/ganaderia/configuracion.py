"""Configuración del Módulo Ganadero (052 T025). Todo por nombre, sin ids en pantalla.

Cada sección es una tabla Gan* con sus campos editables. GET devuelve filas + opciones de los desplegables; PUT
actualiza una fila (id) o da de alta una nueva (id null) en las secciones que lo admiten. Las restricciones de la
base (p. ej. el reparto debe sumar 100) se devuelven como error legible.
"""

from __future__ import annotations

from src.db.connection import execute_write, fetch_all

MESES = [{"id": i, "nombre": n} for i, n in enumerate(
    ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre",
     "Diciembre"], start=1)]
OPCIONES = {
    "categoria": "SELECT IdCategoria id, Nombre nombre FROM dbo.GanCategoria WHERE Activo = 1 ORDER BY Orden",
    "cultivo": "SELECT IdCultivo id, Cultivo nombre FROM dbo.Cultivos ORDER BY Cultivo",
    "rubro": "SELECT IdRubro id, Rubro nombre FROM dbo.Rubros ORDER BY Rubro",
    "lote": "SELECT IdLote id, [Numero Lote] nombre FROM dbo.Lotes ORDER BY [Numero Lote]",
    "contacto_personal": "SELECT IdContacto id, [Razon Social] nombre FROM dbo.Contactos WHERE IdContacto IN "
                         "(SELECT IdContacto FROM dbo.GanReparto WHERE IdContacto IS NOT NULL)",
    "mes": None,
    "tratamiento": [{"id": "Consumo", "nombre": "Se consume"}, {"id": "Amortiza", "nombre": "Se amortiza"}],
    "grupo": [{"id": g, "nombre": g} for g in ("Comercializacion", "Alimentacion", "Sanidad", "Personal", "Otros")],
}


def _c(key, label, tipo="num", columna=None, opciones=None, edita=True, alta=False, max_=None):
    return {"key": key, "label": label, "tipo": tipo, "columna": columna or key, "opciones": opciones, "edita": edita,
            "alta": alta or edita, "max": max_}


SECCIONES = {
    "categorias": {
        "titulo": "Categorías de hacienda", "tabla": "GanCategoria", "pk": "IdCategoria", "alta": False,
        "ayuda": "Equivalente vaca y peso típico se usan cuando la venta o el recuento no traen kg.",
        "sql": "SELECT IdCategoria id, Nombre, CoefEV, PesoTipicoKg, Orden FROM dbo.GanCategoria WHERE Activo = 1 ORDER BY Orden",
        "campos": [_c("Nombre", "Categoría", "texto", edita=False), _c("CoefEV", "Equivalente vaca"),
                   _c("PesoTipicoKg", "Peso típico (kg)")]},
    "alias": {
        "titulo": "Nombres en ventas y planillas", "tabla": "GanCategoriaAlias", "pk": "IdAlias", "alta": True,
        "ayuda": "Cómo se llama cada categoría en liquidaciones, actas y planillas.",
        "sql": "SELECT IdAlias id, Texto, IdCategoria, EsTerceros FROM dbo.GanCategoriaAlias ORDER BY Texto",
        "campos": [_c("Texto", "Nombre", "texto", max_=80), _c("IdCategoria", "Categoría", "opcion", opciones="categoria"),
                   _c("EsTerceros", "De terceros", "si_no")]},
    "rubros": {
        "titulo": "Rubros del resultado", "tabla": "GanRubroMapa", "pk": "IdRubroMapa", "alta": True,
        "ayuda": "A qué fila del resultado ganadero va cada rubro de compras.",
        "sql": "SELECT IdRubroMapa id, RubroPlanilla, Grupo, Orden, IdRubro, IdCultivo FROM dbo.GanRubroMapa ORDER BY Orden",
        "campos": [_c("RubroPlanilla", "Fila del resultado", "texto", max_=80),
                   _c("Grupo", "Grupo", "opcion", opciones="grupo"), _c("Orden", "Orden", "int"),
                   _c("IdRubro", "Rubro de compras", "opcion", opciones="rubro"),
                   _c("IdCultivo", "Cultivo", "opcion", opciones="cultivo")]},
    "forrajes": {
        "titulo": "Forrajes", "tabla": "GanForrajeRegla", "pk": "IdCultivo", "alta": True,
        "ayuda": "Cómo entra el costo de cada cultivo ganadero: en el ejercicio en que se consume o amortizado en años.",
        "sql": "SELECT IdCultivo id, IdCultivo, Tratamiento, Anios, DesfaseEjercicios, Observaciones FROM dbo.GanForrajeRegla",
        "campos": [_c("IdCultivo", "Cultivo", "opcion", opciones="cultivo", edita=False, alta=True),
                   _c("Tratamiento", "Tratamiento", "opcion", opciones="tratamiento"), _c("Anios", "Años", "int"),
                   _c("DesfaseEjercicios", "Ejercicios de desfase", "int"),
                   _c("Observaciones", "Observaciones", "texto", max_=200)]},
    "calendario": {
        "titulo": "Calendario de cultivos agrícolas", "tabla": "GanCalendarioCultivo", "pk": "IdCultivo", "alta": True,
        "ayuda": "Meses que el lote está ocupado por agricultura; el resto del año cuenta como superficie ganadera.",
        "sql": "SELECT IdCultivo id, IdCultivo, MesDesde, MesHasta FROM dbo.GanCalendarioCultivo",
        "campos": [_c("IdCultivo", "Cultivo", "opcion", opciones="cultivo", edita=False, alta=True),
                   _c("MesDesde", "Desde", "opcion", opciones="mes"), _c("MesHasta", "Hasta", "opcion", opciones="mes")]},
    "reparto": {
        "titulo": "Reparto del personal permanente", "tabla": "GanReparto", "pk": "IdReparto", "alta": True,
        "ayuda": "Parte de los haberes del encargado que va a cada actividad. Sin ejercicio = vale para todos. Suma 100 %.",
        "sql": "SELECT IdReparto id, Concepto, Ejercicio, IdContacto, PctGanaderia, PctEstructura, PctAgricultura "
               "FROM dbo.GanReparto ORDER BY Concepto, Ejercicio",
        "campos": [_c("Concepto", "Concepto", "texto", max_=60), _c("Ejercicio", "Ejercicio (ej. 2025/26)", "texto", max_=9),
                   _c("IdContacto", "Persona", "opcion", opciones="contacto_personal"),
                   _c("PctGanaderia", "% Ganadería"), _c("PctEstructura", "% Estructura"),
                   _c("PctAgricultura", "% Agricultura")]},
    "superficie": {
        "titulo": "Superficie del campo", "tabla": "GanSuperficieCampo", "pk": "IdSuperficie", "alta": True,
        "ayuda": "Hectáreas totales o hectáreas ganaderas fijas por período (años de ejercicio).",
        "sql": "SELECT IdSuperficie id, AnioDesde, AnioHasta, TotalHa, HaGanaderasFijas, Fuente FROM dbo.GanSuperficieCampo "
               "ORDER BY AnioDesde",
        "campos": [_c("AnioDesde", "Desde el año", "int"), _c("AnioHasta", "Hasta el año", "int"),
                   _c("TotalHa", "Ha totales"), _c("HaGanaderasFijas", "Ha ganaderas fijas"),
                   _c("Fuente", "Fuente", "texto", max_=200)]},
    "ajustes_superficie": {
        "titulo": "Ajustes de superficie por lote", "tabla": "GanSuperficieAjuste", "pk": "IdAjuste", "alta": True,
        "ayuda": "Reemplaza los meses ganaderos calculados de un lote en un ejercicio. El motivo es obligatorio.",
        "sql": "SELECT IdAjuste id, IdLote, Ejercicio, MesesGanaderos, Motivo FROM dbo.GanSuperficieAjuste ORDER BY Ejercicio",
        "campos": [_c("IdLote", "Lote", "opcion", opciones="lote"), _c("Ejercicio", "Ejercicio (ej. 2025/26)", "texto", max_=9),
                   _c("MesesGanaderos", "Meses ganaderos"), _c("Motivo", "Motivo", "texto", max_=300)]},
    "valuacion": {
        "titulo": "Precio de cierre estimado", "tabla": "GanValuacionRegla", "pk": "IdCategoria", "alta": True,
        "ayuda": "Excepciones a la valuación por INMAG × coeficiente de nuestras ventas (p. ej. toro usado = 500 kg de novillo).",
        "sql": "SELECT IdCategoria id, IdCategoria, KgValuacion, CoefFijo, Motivo FROM dbo.GanValuacionRegla",
        "campos": [_c("IdCategoria", "Categoría", "opcion", opciones="categoria", edita=False, alta=True),
                   _c("KgValuacion", "Kg por cabeza"), _c("CoefFijo", "Coeficiente sobre INMAG"),
                   _c("Motivo", "Motivo", "texto", max_=300)]},
}


def _opciones(clave):
    o = OPCIONES[clave]
    if clave == "mes":
        return MESES
    return o if isinstance(o, list) else fetch_all(o)


def seccion(nombre: str) -> dict:
    s = SECCIONES[nombre]
    ops = {c["opciones"]: _opciones(c["opciones"]) for c in s["campos"] if c["opciones"]}
    return {"seccion": nombre, "titulo": s["titulo"], "ayuda": s["ayuda"], "alta": s["alta"],
            "campos": [{k: c[k] for k in ("key", "label", "tipo", "opciones", "edita", "alta", "max")} for c in s["campos"]],
            "opciones": ops, "filas": fetch_all(s["sql"])}


def todas() -> list[dict]:
    return [{"seccion": k, "titulo": v["titulo"]} for k, v in SECCIONES.items()]


def _valor(c: dict, v):
    if v in (None, ""):
        return None
    if c["tipo"] == "num":
        return float(v)
    if c["tipo"] in ("int",):
        return int(v)
    if c["tipo"] == "si_no":
        return 1 if v in (True, 1, "1", "true") else 0
    if c["tipo"] == "texto":
        t = str(v).strip()
        if c["max"] and len(t) > c["max"]:
            raise ValueError(f"{c['label']}: máximo {c['max']} caracteres")
        return t
    return v


def guardar(nombre: str, id_fila, valores: dict, usuario: str | None) -> None:
    s = SECCIONES[nombre]
    if nombre == "ajustes_superficie" and not str(valores.get("Motivo") or "").strip():
        raise ValueError("El ajuste de superficie necesita un motivo")
    campos = [c for c in s["campos"] if (c["edita"] if id_fila is not None else c["alta"]) and c["key"] in valores]
    if not campos:
        raise ValueError("Nada para guardar")
    vals = tuple(_valor(c, valores[c["key"]]) for c in campos)
    try:
        if id_fila is not None:
            sets = ", ".join(f"[{c['columna']}] = ?" for c in campos)
            execute_write(f"UPDATE dbo.{s['tabla']} SET {sets} WHERE [{s['pk']}] = ?", vals + (id_fila,))
        else:
            if not s["alta"]:
                raise ValueError("Esta sección no admite altas")
            cols = [c["columna"] for c in campos]
            if nombre == "ajustes_superficie":
                cols, vals = cols + ["Usuario"], vals + (usuario,)
            execute_write(f"INSERT INTO dbo.{s['tabla']} ({', '.join(f'[{x}]' for x in cols)}) "
                          f"VALUES ({', '.join('?' for _ in cols)})", vals)
    except ValueError:
        raise
    except Exception as exc:
        m = str(exc)
        if "CK_GanReparto_Suma" in m:
            raise ValueError("Los porcentajes deben sumar 100") from exc
        if "UNIQUE" in m or "duplicate" in m.lower() or "PRIMARY KEY" in m:
            raise ValueError("Ya existe una fila con esos datos") from exc
        if "CHECK" in m:
            raise ValueError("Algún valor está fuera de lo permitido") from exc
        raise
    from src.features.ganaderia import controles, costos, stock, valuacion

    costos.invalidar()
    controles.invalidar()
    valuacion._cache.clear()
    if hasattr(stock, "_cache"):
        stock._cache.clear()


def borrar(nombre: str, id_fila) -> None:
    """Solo en secciones de excepciones (alias, ajustes, reglas de valuación)."""
    s = SECCIONES[nombre]
    if nombre not in ("alias", "ajustes_superficie", "valuacion"):
        raise ValueError("Esta sección no admite borrar filas")
    execute_write(f"DELETE FROM dbo.{s['tabla']} WHERE [{s['pk']}] = ?", (id_fila,))
    from src.features.ganaderia import costos

    costos.invalidar()
