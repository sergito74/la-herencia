"""Giamigli de Bolívar (386 = la propia empresa) y Banco Galicia (518): transferencias entre cuentas propias como traspasos
internos de Tesorería, sin contacto (Sergio 21/10/2026: "adelante con la recomendación").

Cada transferencia entre cuentas propias (BNA cuenta 2 ↔ BNA cuenta 3 ↔ Galicia) tenía sus mitades asignadas como movimientos
de cuenta corriente: casi siempre las dos en 386 (se compensaban) y en dos casos una mitad en 518 (05/09/2023 $5.000.000 y
26/04/2024 $6.200.000), que dejaba −$11,2 M en 386 y el opuesto en 518. Pares exactos (mismo día, mismo importe).
Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuentas, invalidar
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, revisión 21/10/2026)'
# (medio sale, id sale, medio entra, id entra)
PARES = [('bna', 18508, 'galicia', 571), ('bna', 18509, 'galicia', 572), ('bna', 18510, 'bna', 18498),
         ('bna', 18511, 'bna', 18499), ('bna', 18512, 'galicia', 613), ('bna', 18513, 'galicia', 614),
         ('bna', 18514, 'bna', 18500), ('bna', 18628, 'galicia', 1388), ('galicia', 1614, 'bna', 18501),
         ('galicia', 1737, 'bna', 18502), ('galicia', 1794, 'bna', 18503), ('galicia', 1845, 'bna', 18504)]
TABLA = {'bna': ('dbo.[Movimientos BNA]', 'IdMovimientoBNA'), 'galicia': ('dbo.[Movimientos Galicia]', 'IdMovimiento')}


def main():
    _assert_target_is_wc()
    print(backup_verificado('giamigli-traspasos-internos-036'))
    st = []
    for ma, ia, mb, ib in PARES:
        for m, i in ((ma, ia), (mb, ib)):
            t, col = TABLA[m]
            st.append((f'UPDATE {t} SET IdContacto=NULL WHERE {col}=? AND IdContacto IN (386,518)', (i,)))
        if not fetch_all('SELECT 1 x FROM dbo.TraspasosInternosTesoreria WHERE MedioA=? AND IdMovimientoA=? AND MedioB=? AND IdMovimientoB=?', (ma, ia, mb, ib)):
            st.append(("INSERT INTO dbo.TraspasosInternosTesoreria (MedioA,IdMovimientoA,MedioB,IdMovimientoB,Accion,Usuario) VALUES (?,?,?,?,'Vincular',?)",
                        (ma, ia, mb, ib, USUARIO)))
    with reconciliation_transaction():
        execute_write_transaction(st)
    invalidar()
    for c, x in cargar_cuentas([386, 518]).items():
        print(c, x['saldoPesos'])


if __name__ == '__main__': main()
