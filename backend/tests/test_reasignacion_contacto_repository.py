"""Tests de `reasignacion_contacto.repository` — monkeypatch sobre los
puntos de entrada a `WC`, no se escribe contra la base real en tests
automatizados (mismo criterio que 019/020/021)."""

from __future__ import annotations

import pytest

from src.features.reasignacion_contacto import repository


def test_reasignar_inserta_fila_con_contacto_anterior_y_nuevo(monkeypatch):
    monkeypatch.setattr(repository, "_contacto_efectivo", lambda origen, id_origen: 605)
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): {"x": 1})

    statements_capturados = []

    def _fake_transaction(statements):
        statements_capturados.extend(statements)
        return [7]

    monkeypatch.setattr(repository, "execute_write_transaction", _fake_transaction)
    monkeypatch.setattr(repository, "_reasignacion_por_id", lambda idr: {"idReasignacion": idr})

    resultado = repository.reasignar("Galicia", 2712, 1652, "sgiamberardini", motivo="Encode S.A.")

    assert resultado == {"idReasignacion": 7}
    sql, params = statements_capturados[0]
    assert "ReasignacionesContacto" in sql
    assert params == ("Galicia", 2712, 605, 1652, "Encode S.A.", "sgiamberardini")


def test_reasignar_rechaza_si_contacto_nuevo_es_igual_al_efectivo_actual(monkeypatch):
    # Cubre tanto el contacto original como una reasignación previa vigente:
    # `_contacto_efectivo` ya encapsula esa resolución.
    monkeypatch.setattr(repository, "_contacto_efectivo", lambda origen, id_origen: 1652)
    with pytest.raises(ValueError, match="ya está asignado a ese contacto"):
        repository.reasignar("Galicia", 2712, 1652, "u")


def test_reasignar_rechaza_origen_no_soportado():
    with pytest.raises(ValueError, match="El origen 'Impuestos' todavía no admite reasignación."):
        repository.reasignar("Impuestos", 1, 119, "u")


def test_reasignar_rechaza_si_contacto_nuevo_no_existe(monkeypatch):
    monkeypatch.setattr(repository, "_contacto_efectivo", lambda origen, id_origen: 605)
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): None)
    with pytest.raises(ValueError, match="no existe"):
        repository.reasignar("Galicia", 2712, 999999, "u")


def test_listar_historial_de_un_movimiento_devuelve_todas_las_reasignaciones_no_solo_la_ultima(monkeypatch):
    llamadas = []

    def _fake_fetch_all(sql, params=()):
        llamadas.append((sql, params))
        return [
            {"idReasignacion": 2, "origen": "Galicia", "idOrigen": 2712, "idContactoAnterior": 605,
             "idContactoNuevo": 1652, "contactoAnterior": "Carbajo", "contactoNuevo": "Encode",
             "motivo": None, "usuario": "u", "fecha": "2026-09-25"},
            {"idReasignacion": 1, "origen": "Galicia", "idOrigen": 2712, "idContactoAnterior": 1,
             "idContactoNuevo": 605, "contactoAnterior": "X", "contactoNuevo": "Carbajo",
             "motivo": None, "usuario": "u", "fecha": "2026-09-20"},
        ]

    monkeypatch.setattr(repository, "fetch_all", _fake_fetch_all)
    resultado = repository.listar_historial(origen="Galicia", id_origen=2712)
    assert len(resultado) == 2
    sql, params = llamadas[0]
    assert "Origen = ?" in sql and "IdOrigen = ?" in sql
    assert params == ("Galicia", 2712)


def test_listar_historial_sin_filtro_devuelve_todas_las_reasignaciones_ordenadas_por_fecha(monkeypatch):
    llamadas = []

    def _fake_fetch_all(sql, params=()):
        llamadas.append((sql, params))
        return []

    monkeypatch.setattr(repository, "fetch_all", _fake_fetch_all)
    repository.listar_historial()
    sql, params = llamadas[0]
    assert "Origen = ?" not in sql
    assert params == ()


def test_reasignar_vinculo_tarjeta_no_modifica_compras(monkeypatch):
    """FR-014, remediación E1 de /speckit-analyze: ninguna sentencia SQL
    generada por reasignar(origen='Tarjetas', ...) debe referenciar la
    tabla Compras — solo debe escribir en ReasignacionesContacto."""
    monkeypatch.setattr(repository, "_contacto_efectivo", lambda origen, id_origen: 605)
    monkeypatch.setattr(repository, "fetch_one", lambda sql, params=(): {"x": 1})

    statements_capturados = []

    def _fake_transaction(statements):
        statements_capturados.extend(statements)
        return [7]

    monkeypatch.setattr(repository, "execute_write_transaction", _fake_transaction)
    monkeypatch.setattr(repository, "_reasignacion_por_id", lambda idr: {"idReasignacion": idr})

    repository.reasignar("Tarjetas", 3007, 1652, "u")

    for sql, _params in statements_capturados:
        assert "Compras" not in sql
        assert "ReasignacionesContacto" in sql


def test_reasignar_concurrente_conserva_ambas_reasignaciones(monkeypatch):
    """FR-012, remediación E2 de /speckit-analyze: dos reasignaciones
    sucesivas sobre el mismo (Origen, IdOrigen) quedan ambas persistidas;
    _contacto_efectivo siempre devuelve la de mayor IdReasignacion."""
    filas_reales: list[dict] = []

    def _fake_fetch_one(sql, params=()):
        if "Contactos" in sql and "IdContacto = ?" in sql and "TOP 1" not in sql:
            return {"x": 1}
        if "ReasignacionesContacto" in sql:
            if not filas_reales:
                return None
            return max(filas_reales, key=lambda f: f["IdReasignacion"])
        if "Movimientos Galicia" in sql:
            return {"IdContacto": 605}
        return None

    monkeypatch.setattr(repository, "fetch_one", _fake_fetch_one)

    contador = {"n": 0}

    def _fake_transaction(statements):
        contador["n"] += 1
        sql, params = statements[0]
        origen, id_origen, contacto_anterior, contacto_nuevo, motivo, usuario = params
        filas_reales.append(
            {"IdReasignacion": contador["n"], "IdContactoNuevo": contacto_nuevo}
        )
        return [contador["n"]]

    monkeypatch.setattr(repository, "execute_write_transaction", _fake_transaction)
    monkeypatch.setattr(repository, "_reasignacion_por_id", lambda idr: {"idReasignacion": idr})

    repository.reasignar("Galicia", 2712, 1652, "u1")
    repository.reasignar("Galicia", 2712, 999, "u2")

    assert len(filas_reales) == 2
    assert repository._contacto_efectivo("Galicia", 2712) == 999


def test_reasignar_origen_conciliacion_tesoreria_resuelve_contacto_original_desde_conciliaciones(monkeypatch):
    """023-conciliacion-tesoreria FR-008a: 'Conciliación Tesorería' es un
    origen soportado, y su contacto original se resuelve consultando
    dbo.ConciliacionesTesoreria por IdConciliacion (= IdOrigen), no una
    tabla por medio."""
    def _fake_fetch_one(sql, params=()):
        if "ConciliacionesTesoreria" in sql:
            return {"IdContacto": 42}
        if "ReasignacionesContacto" in sql:
            return None  # sin override previo — usa el contacto original
        return {"x": 1}  # contacto nuevo existe

    monkeypatch.setattr(repository, "fetch_one", _fake_fetch_one)

    statements_capturados = []

    def _fake_transaction(statements):
        statements_capturados.extend(statements)
        return [9]

    monkeypatch.setattr(repository, "execute_write_transaction", _fake_transaction)
    monkeypatch.setattr(repository, "_reasignacion_por_id", lambda idr: {"idReasignacion": idr})

    repository.reasignar("Conciliación Tesorería", 88, 1652, "u")

    sql, params = statements_capturados[0]
    assert params == ("Conciliación Tesorería", 88, 42, 1652, None, "u")


def test_reasignar_rechaza_reasignar_al_contacto_ya_vigente_tras_reasignacion_previa(monkeypatch):
    monkeypatch.setattr(repository, "_contacto_efectivo", lambda origen, id_origen: 999)
    with pytest.raises(ValueError, match="ya está asignado a ese contacto"):
        repository.reasignar("Galicia", 2712, 999, "u")


# --- Detección de candidatos (US2) ---------------------------------------


def _fake_fetch_all_deteccion(contactos, movimiento_galicia, movimiento_bna=None):
    def _fake(sql, params=()):
        if "Contactos" in sql:
            return contactos
        if "Movimientos Galicia" in sql:
            return movimiento_galicia
        if "Movimientos BNA" in sql:
            return movimiento_bna or []
        raise AssertionError(f"consulta no esperada: {sql}")

    return _fake


def test_detectar_candidatos_excluye_terminos_de_ruido_bancario(monkeypatch):
    contactos = [{"IdContacto": 518, "razon": "Banco Galicia"}]
    movimiento = [
        {"idOrigen": 1, "fecha": "2025-01-01", "descripcion": "SERVICIO PAGO A PROVEEDORES BANCO DE GALICIA Y B",
         "idContactoActual": 47, "Débitos": 100.0, "Créditos": 0.0}
    ]
    monkeypatch.setattr(repository, "fetch_all", _fake_fetch_all_deteccion(contactos, movimiento))
    monkeypatch.setattr(repository, "_contacto_efectivo", lambda origen, id_origen: 47)
    monkeypatch.setattr(repository, "_ya_descartado", lambda *a: False)

    candidatos = repository.detectar_candidatos()

    assert candidatos == []


def test_detectar_candidatos_encuentra_el_caso_real_encode(monkeypatch):
    contactos = [{"IdContacto": 1652, "razon": "Encode S.A."}]
    movimiento = [
        {"idOrigen": 2712, "fecha": "2025-08-01",
         "descripcion": "TRF INMED PROVEED Encode S.A. 30711103534 VARIOS BANCO DE LA NACION A",
         "idContactoActual": 605, "Débitos": 159720.0, "Créditos": 0.0}
    ]
    monkeypatch.setattr(repository, "fetch_all", _fake_fetch_all_deteccion(contactos, movimiento))
    monkeypatch.setattr(repository, "_contacto_efectivo", lambda origen, id_origen: 605)
    monkeypatch.setattr(repository, "_ya_descartado", lambda *a: False)

    candidatos = repository.detectar_candidatos()

    assert len(candidatos) == 1
    assert candidatos[0]["idContactoSugerido"] == 1652
    assert candidatos[0]["origen"] == "Galicia"
    assert candidatos[0]["idOrigen"] == 2712


def test_detectar_candidatos_excluye_ya_descartados(monkeypatch):
    contactos = [{"IdContacto": 1652, "razon": "Encode S.A."}]
    movimiento = [
        {"idOrigen": 2712, "fecha": "2025-08-01", "descripcion": "TRF INMED PROVEED Encode S.A. VARIOS",
         "idContactoActual": 605, "Débitos": 159720.0, "Créditos": 0.0}
    ]
    monkeypatch.setattr(repository, "fetch_all", _fake_fetch_all_deteccion(contactos, movimiento))
    monkeypatch.setattr(repository, "_contacto_efectivo", lambda origen, id_origen: 605)
    monkeypatch.setattr(repository, "_ya_descartado", lambda *a: True)

    assert repository.detectar_candidatos() == []


def test_detectar_candidatos_excluye_si_contacto_sugerido_ya_es_el_efectivo(monkeypatch):
    contactos = [{"IdContacto": 1652, "razon": "Encode S.A."}]
    movimiento = [
        {"idOrigen": 2712, "fecha": "2025-08-01", "descripcion": "TRF INMED PROVEED Encode S.A. VARIOS",
         "idContactoActual": 1652, "Débitos": 159720.0, "Créditos": 0.0}
    ]
    monkeypatch.setattr(repository, "fetch_all", _fake_fetch_all_deteccion(contactos, movimiento))
    # Ya reasignado a Encode (override vigente) — no debe volver a sugerirse a sí mismo.
    monkeypatch.setattr(repository, "_contacto_efectivo", lambda origen, id_origen: 1652)
    monkeypatch.setattr(repository, "_ya_descartado", lambda *a: False)

    assert repository.detectar_candidatos() == []


def test_descartar_candidato_es_idempotente(monkeypatch):
    llamadas = []

    def _fake_transaction(statements):
        llamadas.append(statements)
        return [1]

    estado = {"existe": False}
    monkeypatch.setattr(repository, "_ya_descartado", lambda *a: estado["existe"])
    monkeypatch.setattr(repository, "execute_write_transaction", _fake_transaction)

    repository.descartar_candidato("Galicia", 2633, 575, "u")
    estado["existe"] = True
    repository.descartar_candidato("Galicia", 2633, 575, "u")

    assert len(llamadas) == 1
