"""Cargill (258): últimos residuos del cruce con el libro del portal.

- LPG 330123062992 (IdVenta 192, 28/03/2023): faltaba la retención IIBB 0,75% certificado 2023-01-00007880 por $1.043,57
  ([Otra Retenciones]); PDF archivado en Dropbox/Ventas/Retenciones 04 2022 - 03 2023.
- NC 7050-00183399 (07/07/2025, US$ 0,51): Tipo de Cambio 1 -> 1.240 (el del PDF/portal, $632,40).
Idempotente.
"""
import shutil
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

ROOT = Path(__file__).resolve().parents[2] / 'backups/cargill-conciliacion-20261020'
DESTINO = Path(r'C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Ventas\Retenciones 04 2022 - 03 2023\30712114602_RETIIBB_20230100007880.pdf')


def main():
    _assert_target_is_wc()
    v = fetch_all("SELECT [Otra Retenciones] o FROM dbo.[Venta Granos] WHERE IdVenta=192 AND IdConsignatario=258 AND [Nro Documento]='330123062992'")[0]
    c = fetch_all("SELECT IdDeuda,[Tipo de Cambio] tc FROM dbo.Compras WHERE IdContacto=258 AND [Nro Documento]='7050-00183399'")[0]
    if not DESTINO.exists():
        shutil.copy2(ROOT / 'portal_docs' / '$B_20230100007880.pdf', DESTINO)
    if abs(v['o'] - 1043.57) < 0.001 and c['tc'] == 1240:
        print('Nada pendiente.'); return
    print(backup_verificado('cargill-residuos-036'))
    with reconciliation_transaction():
        execute_write_transaction([("UPDATE dbo.[Venta Granos] SET [Otra Retenciones]=1043.57 WHERE IdVenta=192 AND IdConsignatario=258", ()),
                                   ('UPDATE dbo.Compras SET [Tipo de Cambio]=1240 WHERE IdDeuda=?', (c['IdDeuda'],))])
    print('ok')


if __name__ == '__main__': main()
