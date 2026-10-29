"""044 — Motor del detector: solo lógica, sin base de datos."""
from datetime import date, timedelta

from src.features.facturas_faltantes.motor import Comprobante, Perfil, aprender_ciclo, compatible, evaluar


def mensuales(desde: date, n: int, saltar=(), importe=100.0):
    out, d = [], desde
    for i in range(n):
        if i not in saltar:
            out.append(Comprobante(fecha=d, importe=importe + i))
        d = date(d.year + (d.month // 12), d.month % 12 + 1, d.day)
    return out


def test_mensual_detecta_el_mes_faltante_aunque_haya_otro_comprobante_cerca():
    c = mensuales(date(2025, 1, 14), 12, saltar=(5,))  # falta jun-2025
    c.append(Comprobante(fecha=date(2025, 6, 2), importe=5.0))  # comprobante suelto que en un control por mes lo tapaba
    ciclo = aprender_ciclo([x.fecha for x in c], date(2026, 1, 1))
    assert ciclo == 30
    r = evaluar([x for x in c if x.importe > 50], Perfil(ciclo=ciclo), date(2026, 1, 1))
    assert [p.esperada.month for p in r.faltantes] == [6]


def test_bimestral_no_marca_meses_intermedios():
    c, d = [], date(2025, 1, 10)
    for _ in range(10):
        c.append(Comprobante(fecha=d, importe=200))
        d += timedelta(days=61)
    assert aprender_ciclo([x.fecha for x in c], d) == 60
    r = evaluar(c, Perfil(ciclo=60), c[-1].fecha + timedelta(days=40))
    assert r.faltantes == [] and r.actual.estado == "pendiente"
    assert evaluar(c, Perfil(ciclo=60), c[-1].fecha + timedelta(days=80)).actual.estado == "pendiente"


def test_pocas_facturas_no_tienen_ciclo():
    assert aprender_ciclo([date(2026, m, 1) for m in range(1, 5)], date(2026, 6, 1)) is None


def test_estados_del_periodo_en_curso():
    c = mensuales(date(2025, 1, 10), 12)
    ultima = c[-1].fecha
    assert evaluar(c, Perfil(ciclo=30), ultima + timedelta(days=5)).actual.estado == "llego"
    assert evaluar(c, Perfil(ciclo=30), ultima + timedelta(days=35)).actual.estado == "pendiente"
    assert evaluar(c, Perfil(ciclo=30), ultima + timedelta(days=50)).actual.estado == "atrasada"
    assert evaluar(c, Perfil(ciclo=30), ultima + timedelta(days=120)).actual.estado == "baja"
    assert evaluar(c, Perfil(ciclo=30, dado_de_baja=True), ultima + timedelta(days=120)).actual is None


def test_cambio_de_monto_mayor_al_30_por_ciento():
    c = mensuales(date(2025, 1, 10), 6)
    c.append(Comprobante(fecha=c[-1].fecha + timedelta(days=30), importe=500))
    r = evaluar(c, Perfil(ciclo=30), c[-1].fecha + timedelta(days=3))
    assert r.actual.cambio_monto


def test_pago_compatible_con_suma_de_hasta_tres():
    assert compatible(300, [100, 120, 80])
    assert not compatible(301, [100, 120, 80])
