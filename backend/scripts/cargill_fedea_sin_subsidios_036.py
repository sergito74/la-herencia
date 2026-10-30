"""036, 30/10/2026: Cargill y FEDEA vuelven a emular sus portales.

Gemini (26/10, soja-bonificaciones-ministerio-mecon-036) cargó los subsidios del Estado como bonificación dentro de dos
ventas de soja: $134.391,10 en la venta 118 (Cargill) y $1.323 en la venta 25 (FEDEA). Ningún comprador los pagó:
- Cargill: libro del portal −$83.951.138,17 (21/10 a 30/10); el sistema difería exactamente en $134.391,10.
- FEDEA: el libro unificado del portal (backups/fedea-portal-20261029) liquida CEC-0003-05644229 por $89.312,91; el
  sistema la tenía en $90.635,91. El par de ajustes 161/162 (29/10) compensaba esos $1.323 en pesos: se borra también.
Se borran Venta Granos_Ajustes 2492 y 2493 y AjustesCuentaCorriente 161 y 162. El registro correcto de los subsidios
(Secretaría de Agricultura, cobrados en el BNA) queda pendiente de la decisión de Sergio.
Uso (desde backend/): python -m scripts.cargill_fedea_sin_subsidios_036 [--aplicar]
"""
import json
import sys

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

CARGILL, FEDEA = 258, 217
PORTAL_CARGILL = -83951138.17
AJUSTES_VENTA = {2492: (118, 134391.10), 2493: (25, 1323.00)}
PAR_FEDEA = {161: ("Deuda", 1664.02), 162: ("Credito", 341.02)}


def saldos():
    bimonetaria.invalidar()
    return {c: bimonetaria.cargar_cuenta(c, refrescar=True) for c in (CARGILL, FEDEA)}


if __name__ == "__main__":
    _assert_target_is_wc()
    filas_v = {r["i"]: r for r in fetch_all("SELECT IdAjuste i, IdVenta v, Importe m, Concepto c FROM dbo.[Venta Granos_Ajustes] "
                                            "WHERE IdAjuste IN (2492, 2493)", ())}
    filas_a = {r["i"]: r for r in fetch_all("SELECT IdAjuste i, IdContacto c, Lado l, Importe m FROM dbo.AjustesCuentaCorriente "
                                            "WHERE IdAjuste IN (161, 162)", ())}
    assert all(filas_v[i]["v"] == v and abs(float(filas_v[i]["m"]) - m) < 0.005 for i, (v, m) in AJUSTES_VENTA.items()), filas_v
    assert all(filas_a[i]["c"] == FEDEA and filas_a[i]["l"] == l and abs(float(filas_a[i]["m"]) - m) < 0.005
               for i, (l, m) in PAR_FEDEA.items()), filas_a
    antes = saldos()
    for c, s in antes.items():
        print("antes", c, s["saldoPesos"], s["saldoDolares"])
    if "--aplicar" not in sys.argv:
        raise SystemExit("Simulación: usar --aplicar para grabar.")
    respaldo = backup_verificado("cargill-fedea-sin-subsidios-036")
    execute_write_transaction([
        ("DELETE FROM dbo.[Venta Granos_Ajustes] WHERE IdAjuste IN (2492, 2493)", ()),
        ("DELETE FROM dbo.AjustesCuentaCorriente WHERE IdAjuste IN (161, 162) AND IdContacto = ?", (FEDEA,)),
        ("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
         "VALUES ('cargill-fedea-sin-subsidios-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
         (json.dumps({"ventaGranosAjustes": {str(k): [v, m] for k, (v, m) in AJUSTES_VENTA.items()},
                      "ajustesFedea": {str(k): [l, m] for k, (l, m) in PAR_FEDEA.items()}}), respaldo,
          "Subsidios de soja sacados de las ventas a Cargill y FEDEA (no los pagó el comprador) y par 161/162 de FEDEA que los "
          "compensaba: Cargill vuelve a igualar su portal; FEDEA iguala la liquidación 05644229 de su libro.")),
    ])
    despues = saldos()
    for c, s in despues.items():
        print("despues", c, s["saldoPesos"], s["saldoDolares"])
    ok_cargill = abs(float(despues[CARGILL]["saldoPesos"]) - PORTAL_CARGILL) < 0.005
    ok_fedea = abs(float(despues[FEDEA]["saldoPesos"])) < 0.005 and abs(float(despues[FEDEA]["saldoDolares"])) < 0.005
    print("Cargill = portal:", ok_cargill, "| FEDEA en $0 y US$0:", ok_fedea)
