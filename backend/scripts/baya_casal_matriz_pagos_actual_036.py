"""Recalcula grupos del relevamiento inicial con la cuenta actual; solo lectura.

No certifica aplicaciones ni reemplaza el cotejo de originales. Separa igualdad
de importe de cierre documental y evita reutilizar diferencias históricas.
"""
import json
from datetime import datetime
from pathlib import Path
from src.features.auditoria_cuentas import bimonetaria as b

ROOT = Path(__file__).resolve().parents[2] / 'backups/baya-conciliacion-20261019'


def main():
    grupos = json.loads((ROOT/'pagos-comparados.json').read_text(encoding='utf-8'))
    filas, compras, entregas = b._vista_en_memoria(True)
    cuenta = filas.get(226, [])
    cot = b.cotizacion_bna()
    ajustes_fuentes = {
        'Canje1801kg faltante': ['Venta Granos 1230'],
        'Dolarizacion saldo pesos de canjes': ['Venta Granos 1231', 'Venta Granos 1232'],
    }
    resultados = []
    for grupo in grupos:
        fuentes = ajustes_fuentes.get(grupo['grupo'], grupo['fuentes'])
        subset = []
        faltantes = []
        for fuente in fuentes:
            origen, identifier = fuente.rsplit(' ', 1)
            found = [r for r in cuenta if r['Origen'] == origen and int(r['IdOrigen']) == int(identifier)]
            if not found: faltantes.append(fuente)
            subset.extend(found)
        actual = b.construir(subset, compras, cot, entregas, False,
                             b._VISTA.get('tc_ventas'), b._VISTA.get('valuaciones'), b._VISTA.get('efectos_valuacion'))
        # Los grupos son de pagos: saldo del subconjunto = crédito neto USD.
        importe = actual['saldoDolares']
        diferencia = round(importe - grupo['creditoProveedor'], 2)
        estado = 'importe_coincidente' if fuentes and not faltantes and abs(diferencia) <= .01 else 'revisar'
        resultados.append(dict(grupo=grupo['grupo'], fuentes=fuentes, faltantes=faltantes,
                               creditoSistemaActual=importe, creditoProveedor=grupo['creditoProveedor'],
                               diferencia=diferencia, estado=estado, evidencia=grupo['evidencia']))
    path = ROOT / f'matriz-pagos-actual-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps({'fecha': datetime.now().isoformat(), 'limite': 'Base externa del relevamiento 19/10; coincidencia numérica no certifica imputaciones ni cierre.', 'grupos': resultados}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'grupos': len(resultados), 'importesCoincidentes': sum(r['estado']=='importe_coincidente' for r in resultados),
                      'revisar': [r for r in resultados if r['estado']=='revisar']}, ensure_ascii=True))
    print(path)


if __name__ == '__main__': main()
