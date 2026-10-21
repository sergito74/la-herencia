"""Cargill (258): valuación en dólares de los anticipos financieros vigentes y cierre de la ficha (spec 036).

- Galicia 3261 (03/06/2026, $83.940.000): anticipos financieros 901517036A (US$ 24.000, girasol 26/27, vence 31/03/2027)
  y 901517055A (US$ 36.000, soja 26/27, vence 30/06/2027) entregados al TC 1.399 (contratos DocuSign 01/06/2026,
  aviso PAGO_COBRO 1980304). ValuacionProveedor: US$ 60.000 (AH 38989/38990; sin fecha de efecto: no puede preceder al banco).
- Saldo externo: libro del portal al 21/10/2026 -$83.951.138,17 (= sistema al centavo) y composición del portal
  $95.777.089,02 (anticipos + ajuste TC 1.525 $7.560.000 + interés 0,8% mensual $4.266.096 no facturados + ND 7050
  76972/77233 vencidas $10.993,02).
- Ficha: cerrada con excepción (ver MotivoExcepcion). Idempotente.
"""
import json
from datetime import date, datetime
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

ROOT = Path(__file__).resolve().parents[2] / 'backups/cargill-conciliacion-20261020'
FUENTE = 'Contratos AF 901517036A/901517055A y composición portal Cargill 21/10/2026'
NOTA = ('Cuenta igual al libro de Cargill al centavo (-$83.951.138,17 al 21/10/2026; cortes 13/05/2016, 04/07/2016, 04/11/2017, '
        '04/05/2018 y cada fecha desde 04/06/2020). Saldo = anticipos financieros US$ 60.000 (901517036A US$ 24.000 vto 31/03/2027 '
        'girasol 26/27; 901517055A US$ 36.000 vto 30/06/2027 soja 26/27; TC 1.399; interés 0,8% mensual a facturar al cancelar) '
        '+ ND 7050-76972/77233 $10.993,02. Detalle: backups/cargill-conciliacion-20261020 y scripts cargill_*_036.')
MOTIVO = ('ND 7050-00076972 ($570,54, vto 25/06/2026) y 7050-00077233 ($10.422,48, vto 02/07/2026) vencidas, a pagar. '
          'El libro de Cargill tiene $145,15 más que sus documentos abiertos (recibo 00151805: remanente $11.513,41 aplicado a FC '
          '5850-12456 el 10/06/2026 vs saldo a favor del libro $11.368,26): inconsistencia interna de Cargill, a consultar; el sistema '
          'sigue al libro. Intereses y diferencia de cambio de los anticipos se registran cuando Cargill los facture.')


def main():
    _assert_target_is_wc()
    ficha = fetch_all('SELECT Estado FROM dbo.RevisionFichas WHERE IdContacto=258')
    val = fetch_all("SELECT * FROM dbo.ValuacionProveedor WHERE Origen='Galicia' AND IdOrigen=3261")
    if val and ficha and ficha[0]['Estado'] == 'cerrada-con-excepcion':
        print('Nada pendiente.'); return
    banco = fetch_all('SELECT [Créditos] c,IdContacto FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=3261')[0]
    assert banco['IdContacto'] == 258 and abs(banco['c'] - 83940000) < 0.01
    antes = cargar_cuenta(258, refrescar=True)
    assert antes['saldoPesos'] == -83951138.17, antes['saldoPesos']
    audit = {'autorizacion': 'Sergio 21/10/2026: valuación US$ y cierre de Cargill', 'fichaAntes': ficha, 'valuacionAntes': val,
             'cuentaAntes': {k: v for k, v in antes.items() if k != 'filas'}, 'backup': backup_verificado('cargill-cierre-036')}
    path = ROOT / f'cierre-{datetime.now():%Y%m%d_%H%M%S}.json'
    with reconciliation_transaction():
        st = []
        if not val:
            st.append(("INSERT INTO dbo.ValuacionProveedor (Origen,IdOrigen,IdContacto,Dolares,Fuente,Nota,Usuario,FechaEfectoUSD,DocumentoEfectoUSD) "
                       "VALUES ('Galicia',3261,258,60000,?,?,'sergio',?,?)",
                       (FUENTE, 'Anticipos financieros US$ 24.000 + US$ 36.000 a TC 1.399 (AH 51240-38989/38990)', None, None)))
        st += [("INSERT INTO dbo.RevisionSaldosExternos (IdContacto,FechaSaldo,Saldo,Moneda,Fuente,Referencia,Nota,Usuario) VALUES (258,?,?,'Pesos','portal',?,?,'sergio')",
                (date(2026, 10, 21), -83951138.17, 'Libro cuenta corriente mycargill (accountbalance/currency)', 'Igual al sistema al centavo.')),
               ("INSERT INTO dbo.RevisionSaldosExternos (IdContacto,FechaSaldo,Saldo,Moneda,Fuente,Referencia,Nota,Usuario) VALUES (258,?,?,'Pesos','portal',?,?,'sergio')",
                (date(2026, 10, 21), -95777089.02, 'Composición del saldo mycargill (isBlnCmpReq=true)',
                 'Incluye ajuste TC 1.525 ($7.560.000) e interés 0,8% mensual ($4.266.096) de los anticipos, aún no facturados.'))]
        if ficha:
            st.append(("UPDATE dbo.RevisionFichas SET Estado='cerrada-con-excepcion',Nota=?,MotivoExcepcion=?,Corte=?,SaldoAlCierre=?,Moneda='Pesos',"
                       "UsuarioCierre='sergio',FechaCierre=SYSDATETIME(),UsuarioActualiza='sergio',FechaActualiza=SYSDATETIME() WHERE IdContacto=258",
                       (NOTA, MOTIVO, date(2026, 10, 21), -83951138.17)))
        else:
            st.append(("INSERT INTO dbo.RevisionFichas (IdContacto,Estado,Nota,MotivoExcepcion,Corte,SaldoAlCierre,Moneda,UsuarioCierre,FechaCierre,UsuarioActualiza) "
                       "VALUES (258,'cerrada-con-excepcion',?,?,?,?,'Pesos','sergio',SYSDATETIME(),'sergio')",
                       (NOTA, MOTIVO, date(2026, 10, 21), -83951138.17)))
        execute_write_transaction(st)
    invalidar()
    despues = cargar_cuenta(258, refrescar=True)
    assert despues['saldoPesos'] == antes['saldoPesos']
    audit['cuentaDespues'] = {k: v for k, v in despues.items() if k != 'filas'}
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(audit['cuentaDespues'], default=str))


if __name__ == '__main__': main()
