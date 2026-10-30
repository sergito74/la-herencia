"""036: los dos renglones de cuadre de Autónomos Lucy (Gemini 26/10/2026) no son impuestos (Sergio 30/10/2026: "de
última, debería ir en la cuenta corriente"). Se pasan de Impuestos a AjustesCuentaCorriente del contacto AFIP (119) con el
mismo lado, importe y fecha: el saldo de la cuenta no cambia. Quedan como diferencia pendiente de conciliar contra el CCMA.
Uso (desde backend/): python -m scripts.autonomos_lucy_cuadre_a_cta_cte_036 [--aplicar]
"""
import json
import sys

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

AFIP = 119
MOTIVO = ("Autónomos Lucy: {} del cierre contra CCMA del 26/10/2026, sacado de Impuestos (no es un impuesto). "
          "Diferencia pendiente de conciliar mes a mes contra el CCMA (Sergio 30/10/2026).")
MOVER = {4810: ("Credito", 3870.38, "reimputaciones CCMA"), 4811: ("Deuda", 21.31, "saldo a favor AFIP")}

if __name__ == '__main__':
    _assert_target_is_wc()
    filas = {r['i']: r for r in fetch_all(f"SELECT IdImpuesto i,Fecha f,Importe m,IdOrganismo o FROM dbo.Impuestos "
                                          f"WHERE IdImpuesto IN ({','.join(map(str, MOVER))})", ())}
    assert set(filas) == set(MOVER) and all(r['o'] == AFIP for r in filas.values()), filas
    antes = bimonetaria.cargar_cuenta(AFIP, refrescar=True)
    print('antes', antes['saldoPesos'], {i: (str(r['f'])[:10], r['m']) for i, r in filas.items()})
    if '--aplicar' not in sys.argv:
        raise SystemExit('Simulación: usar --aplicar para grabar.')
    respaldo = backup_verificado('autonomos-lucy-cuadre-a-cta-cte-036')
    stmts = []
    for i, (lado, importe, que) in MOVER.items():
        stmts.append(("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario) VALUES (?,?,?,?,?,?)",
                      (AFIP, filas[i]['f'], lado, importe, MOTIVO.format(que), 'Sergio (barrida 036)')))
        stmts.append(("DELETE FROM dbo.Impuestos WHERE IdImpuesto=?", (i,)))
    stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES ('autonomos-lucy-cuadre-a-cta-cte-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
                  (json.dumps({str(i): {'lado': l, 'importe': m, 'fecha': str(filas[i]['f'])} for i, (l, m, _) in MOVER.items()}),
                   respaldo, 'Cuadre de Autónomos Lucy (reimputaciones y saldo a favor) movido de Impuestos a ajustes de cuenta corriente AFIP.')))
    execute_write_transaction(stmts)
    bimonetaria.invalidar()
    despues = bimonetaria.cargar_cuenta(AFIP, refrescar=True)
    print('despues', despues['saldoPesos'], 'igual' if abs(float(despues['saldoPesos']) - float(antes['saldoPesos'])) < 0.005 else 'DISTINTO')
