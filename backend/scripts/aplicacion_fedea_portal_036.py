"""036 — grupo 1, FEDEA (217): imputación que emula la cuenta corriente unificada de la extranet de FEDEA.

Sergio 29/10/2026: "FEDEA tiene portal y tenés que respetar su cuenta corriente". La cuenta unificada (bajada en solo
lectura a backups/fedea-portal-20261029/) trae cada movimiento con su saldo, pero los recibos no indican qué
factura cancelan. Se fijan los recibos que FEDEA emitió por el importe exacto de facturas puntuales (PARES) y el resto
va por FIFO estricto en dólares (la cuenta es en US$: "la deuda es en dólares, los pesos son referencia").
Integridad verificada el 29/10: todos los comprobantes y pagos del portal están en el sistema.
Reemplaza las aplicaciones activas de la cuenta. No toca saldos.
Uso (desde backend/): python -m scripts.aplicacion_fedea_portal_036 [--aplicar]
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date

from scripts.aplicacion_baya_portal_036 import _fila
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.auditoria_cuentas import bimonetaria
from src.features.recalculo_fifo import cambio, entrada, motor
from src.features.recalculo_fifo.ejecuciones import _filas_a_escribir
from src.features.vinculos.backup import backup_verificado

C, U = 217, "Sergio (barrida 036)"
NOTA = "FEDEA: recibo por el importe exacto de la factura, según la cuenta unificada de su extranet — barrida 036 29/10/2026"
NOTA_FIFO = "FEDEA: cuenta unificada de la extranet sin imputación por recibo; FIFO estricto en US$ — barrida 036 29/10/2026"
# recibo de FEDEA (pago del sistema) → facturas que cancela por su importe exacto
PARES = {
    ("Tarjetas", 5539): ["0103-00019498"],                       # RC 4869 $22.931,44
    ("Banco Nacion", 16287): ["1003-00001965"],                  # RC 6195 $149.888,08
    ("Banco Nacion", 16288): ["1003-00001966", "1003-00001967", "1003-00001968", "1003-00001969", "1003-00001970"],  # RC 6194 $60.036,04
}

# Compensaciones manuales del cierre del 08/10/2026 (NC 5019 "Reconocimiento comercial" y NC 5018 contra las ND de
# diferencia de cambio de 2022), que el motor no arma solo.
COMPENSACIONES_0810 = [
    {"credito": ("Compras", 2143513722), "debito": ("Compras", 2143522624), "importe": 36735.38, "regla": "manual"},
    {"credito": ("Compras", 2143513722), "debito": ("Compras", 2143513724), "importe": 3771.70, "regla": "manual"},
    {"credito": ("Compras", 2143513723), "debito": ("Compras", 2143513724), "importe": 2426.95, "regla": "manual"},
]

if __name__ == "__main__":
    _assert_target_is_wc()
    hoy = date.today()
    tc = cambio.funcion_tc(hoy)
    e = entrada.armar([C])[C]
    if "--usd" in sys.argv:
        for i in e["items"]:  # la vista trae los documentos en us$ pesificados; el motor los espera en us$
            if i["moneda"] == "USD" and i.get("tcDoc"):
                i["importe"] = round(float(i["importe"]) / i["tcDoc"], 2)
    else:  # cierre del 08/10 hecho en pesos de referencia: todo en pesos
        for i in e["items"]:
            i["moneda"] = "ARS"
    por_nro = {i["nro"]: tuple(i["clave"])[:2] for i in e["items"] if i["clave"][0] == "Compras"}
    fijos = [{"credito": cr, "debito": por_nro[n], "importe": 1e12, "regla": "manual"} for cr, ns in PARES.items() for n in ns]
    fijos += COMPENSACIONES_0810 + e["fijos"]  # compensaciones manuales del cierre del 08/10 (NC 5019 reconocimiento, diferencias de cambio)
    res = motor.recalcular(e["items"], fijos, tc, hoy)
    reglas = defaultdict(lambda: [0, 0.0])
    for a in res["aplicaciones"]:
        reglas[a["regla"]][0] += 1
        reglas[a["regla"]][1] += a["importeArs"]
    print("Aplicaciones por regla:", {k: (v[0], round(v[1], 2)) for k, v in reglas.items()})
    print("Abiertos:", [(i["nro"], i["documento"], round(i["rem"], 2)) for i in res["items"] if i["rem"] > 0.01])
    if "--aplicar" not in sys.argv:
        raise SystemExit("Simulación: usar --aplicar para grabar.")
    print("Respaldo verificado:", backup_verificado("aplicacion-fedea-portal-036"))
    antes = bimonetaria.cargar_cuenta(C, refrescar=True)
    stmts = [("UPDATE a SET Anulada = 1, MotivoAnulacion = ?, UsuarioAnulacion = ?, FechaAnulacion = SYSDATETIME() "
              "FROM dbo.AplicacionesPago a JOIN dbo.Compras c ON c.IdDeuda = a.IdDocumentoAplicado "
              "WHERE c.IdContacto = ? AND a.TipoDocumento = 'CompraDeuda' AND a.Anulada = 0",
              ("Reemplazada por la emulación de la cuenta unificada de FEDEA (barrida 036)", U, C))]
    stmts += [("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, "
               "ImporteAplicado, Fecha, Usuario, Anulada, Origen, NotaConciliacion) VALUES (?, ?, ?, ?, ?, SYSDATETIME(), ?, 0, ?, ?)",
               (f[0], f[1], f[2], f[3], f[4], U, "manual" if f[5] == "manual" else "fifo-032",
                NOTA if f[5] == "manual" else NOTA_FIFO))
              for a in res["aplicaciones"] for f in _filas_a_escribir([_fila(a)])]
    execute_write_transaction(stmts)
    bimonetaria.invalidar()
    despues = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("Saldo antes:", antes["saldoPesos"], antes["saldoDolares"], " después:", despues["saldoPesos"], despues["saldoDolares"])
