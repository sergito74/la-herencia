"""Cuenta 375 (Sergio empleado): sueldos liquidados y no cobrados, períodos enero-2013 a abril-2016 (Sergio 22/10/2026).

Sergio: "creo que no los cobré ni los voy a cobrar". No hay ningún pago en el 375 ni en Empleados.xlsx "Pagos Sergio G" (que
termina en 03/2013) para estos períodos. Un Ajuste Interno (lado Crédito) por cada liquidación, que la cancela: renuncia al
cobro, no pasa a la cuenta de socio. Quedan fuera: diciembre-2012 y anteriores (historia 2011-2012 con Empleados.xlsx), mayo a
julio de 2016 (cobros devueltos a caja, P10-P12) y 2017-2019. Idempotente (Motivo con el IdSalario).
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, cuenta 375 22/10/2026)'


def main():
    _assert_target_is_wc()
    sue = fetch_all("SELECT CONVERT(date,Fecha) f,[Nro Documento] per,Deuda m,IdOrigen i FROM dbo.vw_MovimientosCuenta_Base "
                    "WHERE IdContacto=375 AND Origen='Remuneraciones' AND Fecha BETWEEN '2013-02-01' AND '2016-05-31' ORDER BY Fecha")
    pagos = fetch_all("SELECT COUNT(*) n FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=375 AND Origen<>'Remuneraciones' "
                      "AND Origen<>'Ajuste Interno' AND Fecha BETWEEN '2013-02-01' AND '2016-05-31'")[0]['n']
    assert pagos == 0, f'hay {pagos} pagos en el rango: revisar antes de ajustar'
    st = []
    for s in sue:
        mot = f'Sueldo {s["per"]} no cobrado: Sergio renuncia al cobro (IdSalario {s["i"]})'
        if not fetch_all('SELECT 1 x FROM dbo.AjustesCuentaCorriente WHERE IdContacto=375 AND Motivo=?', (mot,)):
            st.append(("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario) VALUES (375,?,'Credito',?,?,?)",
                       (s['f'].isoformat() if hasattr(s['f'], 'isoformat') else s['f'], float(s['m']), mot, USUARIO)))
    print(len(sue), 'liquidaciones', round(sum(float(s['m']) for s in sue), 2), '| ajustes nuevos', len(st))
    if st:
        print(backup_verificado('sergio-sueldos-no-cobrados-036'))
        with reconciliation_transaction():
            execute_write_transaction(st)
        invalidar()
    print('375', cargar_cuenta(375, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
