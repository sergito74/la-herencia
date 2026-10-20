"""Retenciones 54 (2022-15) y 183 (2024-40): excepción aprobada por Sergio 20/10/2026.

Bayá nunca las registró: la 54 era el resto de FC292987 (USD 263,79 a TC 124,24) y la 183
completaba el eCheq RI52670 para FC389331/389893 a TC 1.045, pero Bayá aplicó el cheque a
TC 1.031,50 sin ella. Certificados intactos; frente al proveedor valen USD 0.
"""
from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import invalidar

NOTAS = {54: 'Excepción: resto de FC292987 (USD 263,79 a TC 124,24); Bayá no registró el certificado. No se reclama (Sergio 20/10/2026).',
         183: 'Excepción: completaba RI52670 a TC 1.045 para FC389331/389893; Bayá aplicó a TC 1.031,50 sin ella. No se reclama (Sergio 20/10/2026).'}


def main():
    assert not fetch_all("SELECT 1 x FROM dbo.ValuacionProveedor WHERE Origen='Retenciones' AND IdOrigen IN (54,183)")
    print(backup_verificado('baya-retenciones-excepcion-036'))
    with reconciliation_transaction():
        execute_write_transaction([('INSERT INTO dbo.ValuacionProveedor (Origen,IdOrigen,IdContacto,Dolares,Fuente,Nota,Usuario) VALUES (?,?,226,0,?,?,?)',
                                    ('Retenciones', i, 'Libro portal Bayá: no registrada', n, 'sergio')) for i, n in NOTAS.items()])
    invalidar()


if __name__ == '__main__': main()
