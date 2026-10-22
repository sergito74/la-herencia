"""Franco Rodríguez (379) y Armando Mori (376): sueldos 2022 iguales a lo realmente pagado (Sergio 22/10/2026).

Los recibos 5 (Mori $26.600) y 6 (Franco $10.000) se pagaron por transferencia el 02/12/2022 (Galicia Giamigli $18.386 +
ICBC Sergio $8.214 a Mori; ICBC Sergio $10.000 a Franco, comprobantes). Las salidas de caja del 28/11/2022 anotadas como esos
recibos (Mori $8.500, Franco $10.000) fueron un retiro de Sergio (ya en su cuenta de socio, script
socios_retiro_sergio_20221128_036): se quitan de las cuentas de los trabajadores (fila guardada en AuditoriaCorrecciones) y se
renombran en la caja. Los sueldos de Access eran recibo formal + "Bonificación adicional" ajustada a esos pagos; los recibos
formales declaran días completos (altas AFIP) para trabajos de medio día. Se ajusta la bonificación para que cada mes = lo
pagado según la Planilla de trabajos eventuales:
  Franco: oct-22 $2.500 (24/10 ½ día), nov-22 $7.500 (1/11 ½ + 2/11)  → total recibo 6 $10.000.
  Mori:   sep-22 $25.600 (recibo 4), oct-22 $3.900 + nov-22 $22.700 (recibo 5 $26.600), dic-22 $18.400 (recibos 9 y 10).
El pago Particular S de Franco de $10.000 fechado 09/05/2022 es la transferencia ICBC del 02/12/2022: se corrige la fecha.
Idempotente.
"""
import json
import os

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, revisión 22/10/2026)'
CAJA = {1977: (376, 931, 'Mori', 5), 1989: (379, 932, 'Franco', 6)}
# IdSalario: total neto que debe quedar
TOTALES = {1829633045: 2500, 1829633089: 7500, 1829633037: 25600, 1829633038: 3900, 1829633050: 22700, 1829633051: 18400}
NETO = ("ISNULL([Sueldo basico],0)+ISNULL(Antiguedad,0)+ISNULL([Adic futuros aumentos],0)+ISNULL([Dia Gremio],0)+ISNULL(Aguinaldo,0)"
        "+ISNULL(Vacaciones,0)+ISNULL(Ajuste,0)+ISNULL([Ajuste No Remunerativo],0)+ISNULL(Redondeo,0)-ISNULL(Jubilacion,0)-ISNULL([Ley 19032],0)"
        "-ISNULL([Obra Social],0)-ISNULL([Obra Social Acuerdos],0)-ISNULL([Servicio de Sepelio],0)-ISNULL([Aporte Sindical],0)")


def main():
    _assert_target_is_wc()
    resp = backup_verificado('franco-mori-sueldos-2022-036')
    st = []
    for f in fetch_all('SELECT * FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo IN (1977,1989)'):
        c, mov, quien, rec = CAJA[f['IdPagoEfectivo']]
        fila = {k: (str(v) if hasattr(v, 'isoformat') else v) for k, v in f.items()}
        st.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                   "VALUES ('eliminar-pago-duplicado','aplicada',?,?,SYSDATETIME(),?,SYSDATETIME(),?,?)",
                   (json.dumps({'tabla': 'Pagos efectivo', 'fila': fila}, ensure_ascii=False), USUARIO, USUARIO, os.path.basename(resp),
                    f'Salida de caja 28/11/2022 anotada como recibo {rec} de {quien}, pagado por transferencia el 02/12/2022; fue retiro de Sergio')))
        st.append(('DELETE FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=? AND IdContacto=?', (f['IdPagoEfectivo'], c)))
        st.append(("UPDATE dbo.MovimientosCajaEfectivo SET Concepto=?, Detalle=? WHERE IdMovimiento=? AND Concepto LIKE 'Trabajos Hacienda%'",
                   ('Retiro efectivo Sergio Giamberardini', f'Anotado antes como Trabajos Hacienda Recibo {rec} ({quien}); el recibo se pagó por transferencia el 02/12/2022', mov)))
    for i, total in TOTALES.items():
        st.append((f'UPDATE dbo.Remuneraciones SET [Bonificacion adicional]=ROUND(?-({NETO}),2) WHERE IdSalario=?', (total, i)))
    st.append(("UPDATE dbo.[Pagos efectivo] SET Fecha='2022-12-02' WHERE IdPagoEfectivo=2004 AND IdContacto=379 AND CONVERT(date,Fecha)='2022-05-09'", ()))
    with reconciliation_transaction():
        execute_write_transaction(st)
    invalidar()
    for c in (376, 379):
        print(c, 'saldo', cargar_cuenta(c, refrescar=True)['saldoPesos'])
    for r in fetch_all(f'SELECT IdSalario i,[Periodo liquidado] p,[Bonificacion adicional] b,{NETO}+ISNULL([Bonificacion adicional],0) t FROM dbo.Remuneraciones WHERE IdSalario IN ('
                       + ','.join(map(str, TOTALES)) + ')'):
        print(r)


if __name__ == '__main__': main()
