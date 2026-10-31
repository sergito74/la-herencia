"""036, 31/10/2026: obligaciones SICORE 2018-2019 que faltaban en la cuenta ARCA (119).
Cinco débitos BNA pagaron retenciones de Ganancias sin la obligación cargada; eran el saldo arrastrado de $4.686,71 de la
subcuenta SICORE. Respaldo: mails del Estudio Criado y el VEP 540664503 (backups/arca-sicore-2018-2019/).
Uso (desde backend/): python -m scripts.arca_sicore_2018_2019_036 [--aplicar]
"""
import json
import sys
from datetime import date

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_one
from src.features.cuentas_corrientes import arca
from src.features.vinculos.backup import backup_verificado

RESPALDO = r"C:\dev\LaHerencia\backups\arca-sicore-2018-2019"
OBLIGACIONES = [  # fecha, período, importe, número, documento, débito BNA
    ("2018-05-22", "05 2018", 1978.00, "MAIL SICORE 2018-05 Lillini 1688 + Gutierrez 290", "mail-2018-05-11.msg", 15866),
    ("2018-09-04", "08 2018", 295.20, "MAIL SICORE 2018-08 Lillini Eduardo", "mail-2018-08-28.msg", 15875),
    ("2018-12-04", "11 2018", 791.92, "MAIL SICORE 2018-11 Sierra", "mail-2018-12-04.msg", 15881),
    ("2019-01-18", "12 2018", 583.04, "MAIL SICORE 2018-12 Lillini", "mail-2019-01-16.msg", 15883),
    ("2019-04-05", "03 2019", 1038.55, "VEP 540664503", "Ticket VEP.pdf", 15888),
]


def sicore():
    return next(s["saldo"] for s in arca.cuenta(None, date(2026, 9, 30))["resumen"] if s["clave"] == "sicore-ganancias")


if __name__ == "__main__":
    _assert_target_is_wc()
    for f, _, imp, num, _, bna in OBLIGACIONES:
        assert fetch_one("SELECT 1 x FROM dbo.[Movimientos BNA] WHERE IdMovimientoBNA = ? AND ABS(Importe + ?) < 0.005 AND IdContacto = 119", (bna, imp))
        assert not fetch_one("SELECT 1 x FROM dbo.Impuestos WHERE IdOrganismo = 119 AND [Numero de documento] = ?", (num,))
    print("SICORE al 30/09 antes", sicore())
    if "--aplicar" not in sys.argv:
        raise SystemExit("Simulación: usar --aplicar para grabar.")
    respaldo = backup_verificado("arca-sicore-2018-2019-036")
    stmts = [("INSERT INTO dbo.Impuestos (Fecha, IdOrganismo, IdTipoImpuesto, [Periodo liquidado], [Numero de documento], Importe, [Documento Original]) "
              "VALUES (?, 119, 20, ?, ?, ?, ?)", (f, per, num, imp, RESPALDO + "\\" + doc)) for f, per, imp, num, doc, _ in OBLIGACIONES]
    stmts.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                  "VALUES ('arca-sicore-2018-2019-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
                  (json.dumps(OBLIGACIONES), respaldo, "Cinco obligaciones SICORE 2018-2019 documentadas por mails del Estudio "
                   "Criado y VEP, pagadas por BNA; explican el saldo arrastrado de $4.686,71.")))
    execute_write_transaction(stmts)
    print("SICORE al 30/09 después", sicore())
