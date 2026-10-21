"""Guazzaroni Greco (604): auditoría histórica 21/10/2026.

Fuentes: resumen de cuenta corriente de Guazzaroni 01/01/2025-22/06/2026 (mail de Melina García 22/06/2026), aviso de
pago CA 0001-00067635, comprobantes por mail (no-reply@guazzaronigreco.com.ar) y PDFs de Dropbox/Compras.
Resultado: saldo US$ 13.605,79 = FC 0037-3310 (US$ 414,46) + 3313 (US$ 3.271,13), canje directo, vencen 31/12/2026, y
FC 0037-4338 (US$ 9.920,20, financiación, vence 30/05/2027; canje soja 26/27 contrato AI 0001-00001735). No vencido.
Correcciones:
1. Cada comprobante en US$ al total exacto del PDF (Guazzaroni pesifica total x TC: FC 1669 $273.243,60, no 273.247,26).
2. Rutas de PDF incompletas ("04 2025 - 03 2026\\...") -> ruta completa de Dropbox/Compras.
3. Notas de crédito vinculadas a lo que anulan: NC 0023-11801 -> FC 0037-1670; NC 0023-13569 -> FC 0037-3231 y 3233.
Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

C = 604
COMPRAS = r'C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras'
TOTAL_USD = {'0037-00001669': 216.86, '0037-00001670': 483.04, '0023 - 00011801': -483.04, '0037-00003231': 387.20,
             '0037-00003233': 3055.33, '0037-00003310': 414.46, '0037-00003313': 3271.13, '0023-00013569': -3442.53,
             '0037-00004338': 9920.20}
VINCULOS = [('0023 - 00011801', '0037-00001670'), ('0023-00013569', '0037-00003231'), ('0023-00013569', '0037-00003233')]


def main():
    _assert_target_is_wc()
    docs = {x['n']: x for x in fetch_all("SELECT c.IdDeuda i,c.[Nro Documento] n,c.[Documento Original] d,t.GranTotal g,t.TotalDetalleCompra td "
                                         "FROM dbo.Compras c JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda=c.IdDeuda WHERE c.IdContacto=?", (C,))}
    print(backup_verificado('guazzaroni-auditoria-036'))
    st = []
    for n, usd in TOTAL_USD.items():
        x = docs[n]
        if abs(x['g'] - usd) > 1e-6:
            st.append(('UPDATE dbo.Det_Compras SET [Precio Unitario]=[Precio Unitario]*? WHERE IdCompra=?', ((usd - (x['g'] - x['td'])) / x['td'], x['i'])))
        p = (x['d'] or '').split('#')[0]
        if p and not p.startswith(('C:', '..')):
            completa = COMPRAS + '\\' + p
            st.append(('UPDATE dbo.Compras SET [Documento Original]=? WHERE IdDeuda=?', (completa + '#' + completa + '#', x['i'])))
    x = docs['0023 - 00024007']
    p = (x['d'] or '').split('#')[0]
    if p and not p.startswith(('C:', '..')):
        st.append(('UPDATE dbo.Compras SET [Documento Original]=? WHERE IdDeuda=?', (COMPRAS + '\\' + p + '#' + COMPRAS + '\\' + p + '#', x['i'])))
    for a, b in VINCULOS:
        if not fetch_all('SELECT 1 x FROM dbo.CompraDocumentosRelacionados WHERE IdCompra=? AND IdCompraRelacionada=?', (docs[a]['i'], docs[b]['i'])):
            st.append(('INSERT INTO dbo.CompraDocumentosRelacionados (IdCompra,IdCompraRelacionada,CreatedAt) VALUES (?,?,SYSDATETIME())', (docs[a]['i'], docs[b]['i'])))
    if st:
        with reconciliation_transaction():
            execute_write_transaction(st)
    invalidar()
    c = cargar_cuenta(C, refrescar=True)
    corte = [f for f in c['filas'] if str(f['fecha']) <= '2026-06-22'][-1]
    print('al 22/06/2026', corte['saldoPesos'], corte['saldoDolares'], '(Guazzaroni -5.049.258,30 / -3.685,59)')
    print('hoy', c['saldoPesos'], c['saldoDolares'])
    nota = ('Auditada 21/10/2026: igual al resumen Guazzaroni al 22/06/2026 ($5.049.258,30 / US$ 3.685,59). Saldo US$ 13.605,79 = FC 3310+3313 '
            '(canje directo, vto 31/12/2026) + FC 4338 (financiación, vto 30/05/2027, canje soja 26/27 AI 1735): no vencido.')
    with reconciliation_transaction():
        execute_write_transaction([("UPDATE dbo.RevisionFichas SET Nota=?,SaldoAlCierre=?,Moneda='Dolares',UsuarioActualiza='sergio',FechaActualiza=SYSDATETIME() "
                                    "WHERE IdContacto=?", (nota, round(c['saldoDolares'], 2), C))])


if __name__ == '__main__': main()
