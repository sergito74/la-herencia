"""041: impuestos particulares — reglas con un store en memoria (sin WC: pyodbc bloqueado)."""

from datetime import date, datetime
from decimal import Decimal as D
from uuid import uuid4

import pytest

from src.db import connection
from src.features.flujo_caja import atribucion
from src.features.impuestos import particular as P


@pytest.fixture(autouse=True)
def sin_base(monkeypatch):
    monkeypatch.setattr(connection.pyodbc, "connect", lambda *a, **k: (_ for _ in ()).throw(AssertionError("041 intentó conectarse")))


class Mem:
    """Store en memoria con la misma interfaz que SqlStore."""

    def __init__(self):
        self.imp = {3206: {"IdImpuesto": 3206, "Fecha": datetime(2017, 11, 7), "Importe": D("8852.10"), "IdOrganismo": 12, "IdTipoImpuesto": 28},
                    10: {"IdImpuesto": 10, "Fecha": datetime(2024, 5, 2), "Importe": D("10000"), "IdOrganismo": 12, "IdTipoImpuesto": 6}}
        self.socios = {1: "Sergio", 2: "Lucy", 3: "Cond LSC", 4: "Ceci"}
        self.cerradas = set()
        self.movs = {3149: {"IdMovimiento": 3149, "IdSocio": 3, "Tipo": "AsignacionGasto", "Importe": D("8852.10"), "Anulada": False,
                            "Origen": None, "Fecha": datetime(2017, 11, 7), "Motivo": "manual"},
                     3150: {"IdMovimiento": 3150, "IdSocio": 3, "Tipo": "Devolucion", "Importe": D("8852.10"), "Anulada": False,
                            "Origen": None, "Fecha": datetime(2017, 11, 13), "Motivo": "Lucy"}}
        self.cargas_t, self.vinc_t, self.pad, self.aud = {}, {}, {}, []
        self.seq = 5000

    def _n(self):
        self.seq += 1
        return self.seq

    def nombre_socio(self, i): return self.socios.get(i)
    def nombre_organismo(self, imp): return "ARBA"
    def impuesto(self, i, bloquear=False): return self.imp.get(i)
    def cuenta_cerrada(self, s): return s in self.cerradas
    def cargas(self, i): return [dict(c) for c in self.cargas_t.values() if c["IdImpuesto"] == i]
    def cargas_vigentes_de(self, ids): return [dict(c) for c in self.cargas_t.values() if c["IdImpuesto"] in ids and c["Estado"] == "vigente"]
    def carga(self, i, bloquear=False): return dict(self.cargas_t[i]) if i in self.cargas_t else None
    def carga_por_movimiento(self, m): return next((c for c in self.cargas_t.values() if c["IdMovimientoSocio"] == m and c["Estado"] == "vigente"), None)
    def cargas_de_partida(self, p): return [c for c in self.cargas_t.values() if c["Partida"] == p]

    def por_clave(self, tabla, clave):
        t = self.cargas_t if tabla == "carga" else self.vinc_t
        return next((dict(x) for x in t.values() if x["ClaveIdempotencia"] == clave), None)

    def debes_manuales(self, s, imp):
        return [m for m in self.movs.values() if m["IdSocio"] == s and not m["Anulada"] and m["Tipo"] == "AsignacionGasto"
                and m["Origen"] in (None, "Manual") and m["Importe"] == imp]

    def movimiento(self, i, bloquear=False): return self.movs.get(i)

    def insertar_movimiento(self, s, tipo, imp, usd, kg, fecha, origen, id_origen, medio, motivo, usuario):
        i = self._n()
        self.movs[i] = {"IdMovimiento": i, "IdSocio": s, "Tipo": tipo, "Importe": imp, "ImporteUSD": usd, "ImporteKgCarne": kg,
                        "Fecha": fecha, "Origen": origen, "IdOrigen": id_origen, "Anulada": False, "Motivo": motivo}
        return i

    def enlazar_movimiento(self, i, o, io): self.movs[i].update(Origen=o, IdOrigen=io)
    def anular_movimiento(self, i, motivo, u): self.movs[i]["Anulada"] = True

    def insertar_carga(self, imp, s, monto, motivo, partida, oscar, mov, clave, h, u):
        i = self._n()
        self.cargas_t[i] = {"IdCarga": i, "IdImpuesto": imp, "IdSocio": s, "Importe": monto, "Motivo": motivo, "Partida": partida,
                            "TitularOscar": oscar, "IdMovimientoSocio": mov, "Estado": "vigente", "ClaveIdempotencia": clave,
                            "HuellaSolicitud": h, "MotivoAnulacion": None}
        return i

    def anular_carga(self, i, motivo, u): self.cargas_t[i].update(Estado="anulada", MotivoAnulacion=motivo)
    def vinculos(self, c): return [dict(v) for v in self.vinc_t.values() if v["IdCarga"] == c]
    def vinculo(self, i, bloquear=False): return dict(self.vinc_t[i]) if i in self.vinc_t else None
    def vinculos_de_movimiento(self, m): return [dict(v) for v in self.vinc_t.values() if v["IdMovimientoSocio"] == m]

    def insertar_vinculo(self, c, m, imp, clave, h, u):
        if any(v["IdCarga"] == c and v["IdMovimientoSocio"] == m and v["Estado"] == "vigente" for v in self.vinc_t.values()):
            raise AssertionError("índice único filtrado")
        i = self._n()
        self.vinc_t[i] = {"IdVinculo": i, "IdCarga": c, "IdMovimientoSocio": m, "Importe": imp, "Estado": "vigente",
                          "ClaveIdempotencia": clave, "HuellaSolicitud": h}
        return i

    def anular_vinculo(self, i, motivo, u): self.vinc_t[i]["Estado"] = "anulada"
    def padron(self, p): return self.pad.get(p)

    def padron_guardar(self, p, s, o, e, oscar, u):
        self.pad[p] = {"Partida": p, "IdSocio": s, "IdCargaOrigen": o, "Estado": e, "TitularOscar": oscar}

    def auditar(self, *a): self.aud.append(a)


def valuar(imp, fecha):
    from src.features.cuentas_socios.valuacion import calcular
    return calcular(imp, fecha, D("17.65"), D("31"))


def carga(s, imp=3206, **kw):
    cuerpo = {"claveIdempotencia": str(uuid4()), "idSocio": 3, "importe": "8852.10", "motivo": "Complementario del Condominio", **kw}
    if "porcentaje" in kw:
        cuerpo.pop("importe")
    return P.crear_carga(s, imp, cuerpo, "sergio", valuar)


# --- Reglas puras ---------------------------------------------------------------------------------------------------

def test_porcentaje_half_up_sobre_total_y_exclusion():
    assert P.importe_de_carga(D("10000"), porcentaje="33.335") == D("3333.50")
    assert P.importe_de_carga(D("10"), importe="6,005") == D("6.01")
    for a, b in ((None, None), ("1", "1")):
        with pytest.raises(P.ErrorParticular):
            P.importe_de_carga(D("10"), a, b)
    with pytest.raises(P.ErrorParticular):
        P.importe_de_carga(D("10"), porcentaje="101")


def test_partida_normalizada_conserva_ceros_y_puntuacion():
    assert P.normalizar_partida("  011-007957-5   rural ") == "011-007957-5 RURAL"
    assert P.normalizar_partida("   ") is None


def test_huella_canoniza_montos_equivalentes():
    assert P.huella({"importe": "8852.1", "idSocio": 3}, "u") == P.huella({"importe": "8852.10", "idSocio": 3}, "u")
    assert P.huella({"importe": "8852.1"}, "u") != P.huella({"importe": "8852.1"}, "otro")


# --- US1: cargar --------------------------------------------------------------------------------------------------

def test_carga_total_genera_un_debe_enlazado_positivo_a_la_fecha_del_impuesto():
    s = Mem()
    c, creada = carga(s, reemplazarMovimientoManual=3149)
    assert creada and c["estado"] == "vigente" and c["estadoDevolucion"] == "pendiente"
    debe = s.movs[c["idMovimientoSocio"]]
    assert debe["Tipo"] == "AsignacionGasto" and debe["Origen"] == "ImpuestoParticular" and debe["IdOrigen"] == c["idCarga"]
    assert debe["Fecha"] == date(2017, 11, 7)
    assert debe["ImporteUSD"] == D("250.7677")
    assert debe["ImporteKgCarne"] == D("142.776")
    assert s.movs[3149]["Anulada"]  # el manual reemplazado
    assert len([m for m in s.movs.values() if m["Tipo"] == "AsignacionGasto" and not m["Anulada"]]) == 1


def test_debe_manual_equivalente_pide_eleccion_explicita():
    s = Mem()
    with pytest.raises(P.ErrorParticular) as e:
        carga(s)
    assert e.value.codigo == "DEBE_MANUAL_EQUIVALENTE" and e.value.contexto["requiereConfirmacion"]
    assert e.value.contexto["avisos"][0]["candidatos"][0]["idMovimiento"] == 3149
    with pytest.raises(P.ErrorParticular) as e2:
        carga(s, reemplazarMovimientoManual=3150)  # no es un Debe equivalente
    assert e2.value.codigo == "DEBE_MANUAL_INVALIDO"


def test_ventana_de_tres_dias_sobre_la_fecha_historica():
    s = Mem()
    s.movs[3149]["Fecha"] = datetime(2017, 11, 11)  # 4 días: fuera de la ventana
    c, _ = carga(s)
    assert c["estado"] == "vigente" and not s.movs[3149]["Anulada"]


def test_parcial_varios_socios_y_exceso():
    s = Mem()
    carga(s, imp=10, idSocio=1, importe="6000")
    carga(s, imp=10, idSocio=2, porcentaje="40")
    with pytest.raises(P.ErrorParticular) as e:
        carga(s, imp=10, idSocio=4, importe="0.01")
    assert e.value.codigo == "SUPERARIA_IMPORTE" and e.value.contexto["remanente"] == "0.00"
    r = P.consultar(s, 10)
    assert r["aCargoDeSocios"] == "10000.00" and r["parteEmpresa"] == "0.00"


def test_cuenta_cerrada_exige_confirmacion():
    s = Mem()
    s.cerradas.add(1)
    with pytest.raises(P.ErrorParticular) as e:
        carga(s, imp=10, idSocio=1, importe="100")
    assert e.value.codigo == "CUENTA_CERRADA"
    c, _ = carga(s, imp=10, idSocio=1, importe="100", confirmarCuentaCerrada=True)
    assert c["estado"] == "vigente"


def test_idempotencia_misma_clave_y_cuerpo_distinto():
    s = Mem()
    cuerpo = {"claveIdempotencia": "k1", "idSocio": 1, "importe": "100", "motivo": "x"}
    c1, n1 = P.crear_carga(s, 10, dict(cuerpo), "u", valuar)
    c2, n2 = P.crear_carga(s, 10, dict(cuerpo, importe="100.00"), "u", valuar)
    assert n1 and not n2 and c1["idCarga"] == c2["idCarga"] and len(s.cargas_t) == 1
    with pytest.raises(P.ErrorParticular) as e:
        P.crear_carga(s, 10, dict(cuerpo, importe="200"), "u", valuar)
    assert e.value.codigo == "CLAVE_IDEMPOTENCIA_REUTILIZADA"
    P.anular_carga(s, c1["idCarga"], "error", "u")
    c3, n3 = P.crear_carga(s, 10, dict(cuerpo), "u", valuar)  # reintento tras anular: no reactiva
    assert not n3 and c3["estado"] == "anulada"


def test_oscar_siempre_al_condominio():
    s = Mem()
    with pytest.raises(P.ErrorParticular):
        carga(s, imp=10, idSocio=1, importe="10", partida="011-1", titularOscar=True)
    carga(s, imp=10, idSocio=3, importe="10", partida="011-1", titularOscar=True)
    with pytest.raises(P.ErrorParticular) as e:
        carga(s, imp=10, idSocio=2, importe="10", partida=" 011-1 ")
    assert e.value.codigo == "TITULAR_INVALIDO"


# --- US2: devoluciones y padrón ------------------------------------------------------------------------------------

def test_vinculo_a_haber_existente_marca_devuelto_y_respeta_capacidades():
    s = Mem()
    c, _ = carga(s, reemplazarMovimientoManual=3149)
    with pytest.raises(P.ErrorParticular) as e:
        P.vincular_devolucion(s, c["idCarga"], {"claveIdempotencia": "v0", "idMovimientoSocio": 3150, "importe": "9000"}, "u", valuar)
    assert e.value.codigo == "SUPERARIA_PENDIENTE"
    r, _ = P.vincular_devolucion(s, c["idCarga"], {"claveIdempotencia": "v1", "idMovimientoSocio": 3150, "importe": "8852.10"}, "u", valuar)
    assert r["estadoDevolucion"] == "devuelto" and r["pendienteNominal"] == "0.00"
    assert not s.movs[3150]["Anulada"]  # el Haber se conserva, no se crea otro
    assert len([m for m in s.movs.values() if m["Tipo"] == "Devolucion"]) == 1


def test_haber_repartido_600_400_y_exceso_de_capacidad():
    s = Mem()
    s.movs[7000] = {"IdMovimiento": 7000, "IdSocio": 1, "Tipo": "Devolucion", "Importe": D("1000"), "Anulada": False, "Origen": None,
                    "Fecha": datetime(2024, 6, 1)}
    a, _ = carga(s, imp=10, idSocio=1, importe="600")
    b, _ = carga(s, imp=10, idSocio=1, importe="600")
    P.vincular_devolucion(s, a["idCarga"], {"claveIdempotencia": "a", "idMovimientoSocio": 7000, "importe": "600"}, "u", valuar)
    with pytest.raises(P.ErrorParticular) as e:
        P.vincular_devolucion(s, b["idCarga"], {"claveIdempotencia": "b", "idMovimientoSocio": 7000, "importe": "600"}, "u", valuar)
    assert e.value.codigo == "CAPACIDAD_HABER_INSUFICIENTE" and e.value.contexto["disponible"] == "400.00"
    r, _ = P.vincular_devolucion(s, b["idCarga"], {"claveIdempotencia": "c", "idMovimientoSocio": 7000, "importe": "400"}, "u", valuar)
    assert r["estadoDevolucion"] == "parcial" and r["pendienteNominal"] == "200.00"


def test_haber_de_otro_socio_y_haber_nuevo_idempotente():
    s = Mem()
    c, _ = carga(s, imp=10, idSocio=1, importe="500")
    with pytest.raises(P.ErrorParticular) as e:
        P.vincular_devolucion(s, c["idCarga"], {"claveIdempotencia": "x", "idMovimientoSocio": 3150, "importe": "1"}, "u", valuar)
    assert e.value.codigo == "HABER_NO_VALIDO"
    cuerpo = {"claveIdempotencia": "n", "fecha": "2024-06-10", "importe": "500", "medio": "Transferencia", "motivo": "Devolvió"}
    r1, n1 = P.vincular_devolucion(s, c["idCarga"], dict(cuerpo), "u", valuar)
    r2, n2 = P.vincular_devolucion(s, c["idCarga"], dict(cuerpo), "u", valuar)
    nuevos = [m for m in s.movs.values() if m["Origen"] == "DevImpParticular"]
    assert n1 and not n2 and len(nuevos) == 1 and nuevos[0]["IdOrigen"] == c["idCarga"] and r2["estadoDevolucion"] == "devuelto"


def test_padron_unico_ambiguo_y_sin_cargas():
    s = Mem()
    a, _ = carga(s, imp=10, idSocio=1, importe="100", partida="P-1")
    assert P.consultar_partida(s, "p-1")["estado"] == "vigente" and P.consultar_partida(s, "P-1")["idSocio"] == 1
    carga(s, imp=10, idSocio=2, importe="100", partida="P-1")
    info = P.consultar_partida(s, "P-1")
    assert info["estado"] == "ambigua" and info["idSocio"] is None and {c["idSocio"] for c in info["candidatos"]} == {1, 2}
    assert P.consultar_partida(s, "OTRA")["estado"] == "desconocida"
    for c in list(s.cargas_t):
        P.anular_carga(s, c, "x", "u")
    assert P.consultar_partida(s, "P-1")["estado"] == "sin_cargas"


def test_resumen_de_lista_agrega_estados():
    s = Mem()
    a, _ = carga(s, imp=10, idSocio=1, importe="100")
    carga(s, imp=10, idSocio=2, importe="100")
    s.movs[7001] = {"IdMovimiento": 7001, "IdSocio": 1, "Tipo": "Devolucion", "Importe": D("100"), "Anulada": False, "Origen": None}
    P.vincular_devolucion(s, a["idCarga"], {"claveIdempotencia": "z", "idMovimientoSocio": 7001, "importe": "100"}, "u", valuar)
    r = P.resumen_impuestos(s, [10, 3206])
    assert r[10]["estadoDevolucion"] == "parcial" and r[10]["pendienteNominal"] == "100.00" and 3206 not in r


# --- US3: anulación y guardias ---------------------------------------------------------------------------------------

def test_anular_carga_anula_debe_y_vinculos_y_conserva_haber():
    s = Mem()
    c, _ = carga(s, reemplazarMovimientoManual=3149)
    P.vincular_devolucion(s, c["idCarga"], {"claveIdempotencia": "v", "idMovimientoSocio": 3150, "importe": "8852.10"}, "u", valuar)
    r = P.anular_carga(s, c["idCarga"], "cargada por error", "u")
    assert r["estado"] == "anulada" and s.movs[c["idMovimientoSocio"]]["Anulada"] and not s.movs[3150]["Anulada"]
    assert all(v["Estado"] == "anulada" for v in s.vinc_t.values())
    aud = len(s.aud)
    P.anular_carga(s, c["idCarga"], "otra vez", "u")  # repetición sin escrituras
    assert len(s.aud) == aud
    with pytest.raises(P.ErrorParticular):
        P.anular_carga(s, c["idCarga"], "  ", "u")


def test_desvincular_libera_capacidad_y_revincula_con_vinculo_nuevo():
    s = Mem()
    c, _ = carga(s, reemplazarMovimientoManual=3149)
    r, _ = P.vincular_devolucion(s, c["idCarga"], {"claveIdempotencia": "v1", "idMovimientoSocio": 3150, "importe": "8000"}, "u", valuar)
    P.anular_vinculo(s, c["idCarga"], r["idVinculo"], "importe mal", "u")
    r2, _ = P.vincular_devolucion(s, c["idCarga"], {"claveIdempotencia": "v2", "idMovimientoSocio": 3150, "importe": "8852.10"}, "u", valuar)
    assert r2["idVinculo"] != r["idVinculo"] and r2["estadoDevolucion"] == "devuelto" and len(s.vinc_t) == 2


def test_guardia_de_movimientos_vinculados():
    s = Mem()
    c, _ = carga(s, reemplazarMovimientoManual=3149)
    assert P.vinculo_de_movimiento(s, c["idMovimientoSocio"])["rol"] == "debe"
    assert P.vinculo_de_movimiento(s, 3150) is None
    P.vincular_devolucion(s, c["idCarga"], {"claveIdempotencia": "v", "idMovimientoSocio": 3150, "importe": "1"}, "u", valuar)
    assert P.vinculo_de_movimiento(s, 3150)["rol"] == "haber"


# --- Flujo de caja --------------------------------------------------------------------------------------------------

def test_flujo_reparte_la_parte_cargada_a_cuenta_de_socios(monkeypatch):
    monkeypatch.setattr(atribucion, "_rubro_de_impuesto", lambda i, memo: "Impuesto Inmobiliario")
    monkeypatch.setattr(P, "fraccion_a_socios", lambda ids: {10: 0.6})
    partes = atribucion.partes_desde_aplicaciones(
        [{"tipoDocumento": "Impuesto", "idDocumentoAplicado": 10, "importeAplicado": 10000}], 10000, date(2024, 5, 2))
    por = {p["rubro"]: round(p["importe"], 2) for p in partes}
    assert por == {"Cuenta de socios": 6000.0, "Impuesto Inmobiliario": 4000.0}
    assert round(sum(p["importe"] for p in partes), 2) == 10000.0
