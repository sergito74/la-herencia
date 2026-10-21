"""Actualiza el sistema con la versión vigente de `Cajas Giamigli.xlsx` (Sergio 21/10/2026: "actualizá el sistema con
esta planilla"). Re-corre la migración 027 de forma segura:

Cuentas de socios (MovimientosCuentaSocio):
- fila de la planilla que ya está (misma fecha e importe): nada;
- fila nueva cuyo importe (+-$1) coincide con un movimiento migrado (Usuario 'migracion-cajas-giamigli') que ya no está
  en la planilla y es del mismo tipo: la fila se EDITÓ en la planilla -> se actualizan fecha/importe/medio/motivo;
- resto: alta.
Nunca borra: los movimientos del sistema que no están en la planilla (vínculos y ajustes de la revisión 036, ARCA,
validaciones) se listan para revisar.

Cajas GiamigliSA (Caja Efectivo Pesos) y CampoChica (Caja chica campo) (MovimientosCajaEfectivo):
- alta solo si no existe en la caja (misma fecha e importe, sin mirar concepto) ni como Pago efectivo del contacto
  (regla de la migración original). Así re-correr no duplica.

Uso: --simular (default) muestra los cambios; --aplicar escribe (respaldo verificado).
"""
from __future__ import annotations

import sys
from collections import Counter

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, fetch_one, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from scripts.migracion_cajas_giamigli import dedup
from scripts.migracion_cajas_giamigli.lector_excel import leer_hoja_caja, leer_hoja_socio
from scripts.migracion_cajas_giamigli.migrar_socios import HOJA_A_ID_SOCIO, RUTA_EXCEL_DEFAULT, _a_fecha_date

USUARIO = 'migracion-cajas-giamigli'


def plan_socio(hoja: str, id_socio: int):
    filas, _ = leer_hoja_socio(RUTA_EXCEL_DEFAULT, hoja)
    sistema = fetch_all("SELECT IdMovimiento i,Tipo t,Fecha f,Importe m,Usuario u FROM dbo.MovimientosCuentaSocio WHERE IdSocio=? AND Anulada=0", (id_socio,))
    libres = {s['i']: s for s in sistema}
    nuevas = []
    for f in filas:  # coincidencia exacta
        s = next((s for s in libres.values() if _a_fecha_date(s['f']) == f.fecha and abs(s['m'] - f.importe_pesos) <= 0.01), None)
        if s:
            del libres[s['i']]
        else:
            nuevas.append(f)
    altas, ediciones = [], []
    for f in nuevas:  # fila editada en la planilla
        s = next((s for s in libres.values() if s['u'] == USUARIO and s['t'] == f.tipo and abs(s['m'] - f.importe_pesos) <= 1), None)
        if s:
            del libres[s['i']]
            ediciones.append((s, f))
            continue
        # ya cargado a mano en la revisión (compra particular, barrida 036): mismo tipo, importe +-$1, fecha +-10 días
        s = next((s for s in libres.values() if s['t'] == f.tipo and abs(s['m'] - f.importe_pesos) <= 1
                  and abs((_a_fecha_date(s['f']) - f.fecha).days) <= 10), None)
        if s:
            del libres[s['i']]
        else:
            altas.append(f)
    return altas, ediciones, list(libres.values())


def plan_caja(hoja: str, caja: str):
    filas, _ = leer_hoja_caja(RUTA_EXCEL_DEFAULT, hoja, caja)
    existentes = Counter((_a_fecha_date(r['f']), round(r['m'], 2)) for r in
                         fetch_all("SELECT Fecha f,Importe m FROM dbo.MovimientosCajaEfectivo WHERE Caja=?", (caja,)))
    altas = []
    for f in filas:
        k = (f.fecha, round(f.importe, 2))
        if existentes[k] > 0:
            existentes[k] -= 1
            continue
        id_contacto = dedup.resolver_contacto_por_nombre(f.concepto) if caja == 'GiamigliSA' else None
        if id_contacto is not None and dedup.ya_existe_pago_efectivo(id_contacto, f.fecha, f.importe):
            continue
        altas.append((f, id_contacto))
    return altas


def main():
    _assert_target_is_wc()
    aplicar = '--aplicar' in sys.argv
    st = []
    for hoja, socio in HOJA_A_ID_SOCIO.items():
        altas, ediciones, solo_sistema = plan_socio(hoja, socio)
        print(f'== {hoja}: altas {len(altas)}, ediciones {len(ediciones)}, solo en sistema {len(solo_sistema)}')
        for f in altas:
            print('  + ', f.fecha, f.tipo, f.importe_pesos, f'{f.proveedor or ""} — {f.detalle or ""}'[:60], f.forma_pago)
            st.append(("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Medio,Motivo,Usuario) "
                       "VALUES (?,?,?,?,?,?,?,?,?)", (socio, f.tipo, f.importe_pesos, f.importe_usd, f.importe_kg_carne, f.fecha, f.forma_pago,
                                                      f'{f.proveedor or ""} — {f.detalle or ""}'.strip(' —') or None, USUARIO)))
        for s, f in ediciones:
            print('  ~ ', _a_fecha_date(s['f']), s['m'], '->', f.fecha, f.importe_pesos, f'{f.proveedor or ""} — {f.detalle or ""}'[:50])
            st.append(("UPDATE dbo.MovimientosCuentaSocio SET Fecha=?,Importe=?,ImporteUSD=?,ImporteKgCarne=?,Medio=?,Motivo=? WHERE IdMovimiento=?",
                       (f.fecha, f.importe_pesos, f.importe_usd, f.importe_kg_carne, f.forma_pago,
                        f'{f.proveedor or ""} — {f.detalle or ""}'.strip(' —') or None, s['i'])))
        for s in solo_sistema:
            print('  = solo sistema', s['i'], _a_fecha_date(s['f']), s['t'], s['m'], s['u'])
    for hoja, caja in (('Caja Efectivo Pesos', 'GiamigliSA'), ('Caja chica campo', 'CampoChica')):
        altas = plan_caja(hoja, caja)
        print(f'== {hoja}: altas {len(altas)}')
        for f, c in altas:
            print('  + ', f.fecha, f.importe, (f.concepto or '')[:30], '|', (f.detalle or '')[:30])
            st.append(("INSERT INTO dbo.MovimientosCajaEfectivo (Caja,Fecha,Concepto,Detalle,Importe,Cuenta,IdContactoRelacionado,NumeroDocumento,FormaPago,Usuario) "
                       "VALUES (?,?,?,?,?,?,?,?,?,?)", (caja, f.fecha, f.concepto, f.detalle, f.importe, f.cuenta, c, f.numero_documento, f.forma_pago, USUARIO)))
    print(len(st), 'cambios')
    if aplicar and st:
        print(backup_verificado('actualizar-cajas-giamigli'))
        with reconciliation_transaction():
            execute_write_transaction(st)


if __name__ == '__main__': main()
