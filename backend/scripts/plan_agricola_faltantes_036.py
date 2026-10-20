"""Plan agrícola: combinaciones con costos reales que faltaban (aprobado por Sergio 20/10/2026).

- Sorgo 2026/27 lote 9A (15 ha = seguimiento La Esperanza 2026).
- Avena 2015 lotes 6B, 6C, 8A (facturas: 'Has. Avena (L. 6B, 6C, 8A)').
- Avena 2017 lotes 10A y 10B (pulverización 'L. 10' 20,3 ha y 'Lote 10B').
- Cebada 2015/16 lotes 2A, 5A, 5B (luego soja segunda 2015/16; confirmado por Sergio).
Usa planificacion.repository.crear (control de duplicados). Idempotente.
"""
from src.db.connection import _assert_target_is_wc, fetch_all
from src.features.planificacion import repository as plan
from src.features.vinculos.backup import backup_verificado

ALTAS = [('Sorgo', '2026/2027', ['9A']), ('Avena', '2015', ['6B', '6C', '8A']),
         ('Avena', '2017', ['10A', '10B']), ('Cebada', '2015/2016', ['2A', '5A', '5B'])]


def main():
    _assert_target_is_wc()
    cul = {r['n']: r['id'] for r in fetch_all('SELECT IdCultivo AS id, Cultivo AS n FROM dbo.Cultivos')}
    camp = {r['n'].strip(): r['id'] for r in fetch_all('SELECT IdCampaña AS id, Campaña AS n FROM dbo.Campañas')}
    lote = {r['n']: r['id'] for r in fetch_all('SELECT IdLote AS id, [Numero Lote] AS n FROM dbo.Lotes')}
    print(backup_verificado('plan-agricola-faltantes-036'))
    for c, cp, lotes in ALTAS:
        for l in lotes:
            datos = {'idLote': lote[l], 'idCultivo': cul[c], 'idCampania': camp[cp]}
            try:
                print(c, cp, l, '->', plan.crear(datos))
            except ValueError as e:
                print(c, cp, l, 'ya estaba:', e)


if __name__ == '__main__': main()
