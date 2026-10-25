"""036: motosierra Agropark 2016 pagada con la Diners de Lucy (Sergio 25/10/2026: «La tarjeta Diners era de Lucy. La
compensación de las cuotas tiene que hacerse contra su cuenta, no la del condominio»).

Evidencia: rendición del Condominio jun-2016 («Compra Motosierra Giamigli (Diners) 1/6», $2.203,85) y factura Agropark
0005-00000728 ($13.811). Anticipo $588 por BNA (16500), 6 cuotas con la Diners de Lucy; Giamigli le devolvió cada cuota
por transferencia BNA (16502–16507), que estaban imputadas a Agropark.
- 6 pagos «Tarjeta de Crédito No propia» (forma 20, caja Particular L) a Agropark, en las fechas de las transferencias,
  aplicados a la factura 728.
- BNA 16502–16507 pasan al contacto 390 (Lucy, lado bancario).
- Lucy (socio 2): Haber por cada cuota pagada con su tarjeta y Debe por cada reintegro de Giamigli (neto 0).
- Se rehacen las aplicaciones FIFO de Agropark (anticipo → 728, 16501 → 765, NC 0005-020 → 829, cuotas → 728).
Agropark sigue en 0 y Lucy neto 0. Inspección por defecto. Idempotente.
"""

import argparse
import json
from datetime import date
from decimal import Decimal

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.cuentas_socios.valuacion import a_fecha
from src.features.vinculos.backup import backup_verificado

RULE = "motosierra-diners-lucy-036"
AGROPARK, LUCY_CONTACTO, LUCY = 262, 390, 2
BNA = (16502, 16503, 16504, 16505, 16506, 16507)
F728, F765, F829, NC020 = 2143510733, 2143510768, 2143510789, 2143510790
APLIC_FIFO = tuple(range(10912, 10924))
USUARIO = "Claude036"


def _saldo(contacto):
    return Decimal(str(fetch_all("SELECT SUM(ISNULL(Deuda,0)-ISNULL(Credito,0)) s FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=?", (contacto,))[0]["s"] or 0))


def run(aplicar=False):
    _assert_target_is_wc()
    if fetch_all("SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)):
        return {"estado": "ya_aplicado_sin_escrituras"}
    bna = fetch_all("SELECT IdMovimientoBNA i, CONVERT(date,[Fecha / Hora Mov#]) f, -Importe v FROM dbo.[Movimientos BNA] WHERE IdContacto=? AND IdMovimientoBNA IN (%s) ORDER BY 1"
                    % ",".join(map(str, BNA)), (AGROPARK,))
    assert len(bna) == 6, bna
    apl = fetch_all("SELECT IdAplicacion FROM dbo.AplicacionesPago WHERE Anulada=0 AND IdAplicacion IN (%s)" % ",".join(map(str, APLIC_FIFO)))
    assert len(apl) == len(APLIC_FIFO), apl
    total = sum(Decimal(str(b["v"])) for b in bna)
    res = {"estado": "inspeccion", "cuotas": [(b["i"], str(b["f"]), str(b["v"])) for b in bna], "total": str(total),
           "saldoAgropark": str(_saldo(AGROPARK))}
    if not aplicar:
        return res
    res["backup"] = backup_verificado("motosierra_diners_lucy_036")
    op = fetch_all("SELECT MAX(IdOperacion) m FROM dbo.[Pagos efectivo]")[0]["m"] + 1
    st = [("UPDATE dbo.AplicacionesPago SET Anulada=1, MotivoAnulacion=?, UsuarioAnulacion=?, FechaAnulacion=SYSDATETIME() WHERE IdAplicacion=? AND Anulada=0",
           ("036: motosierra pagada con Diners de Lucy; se rehacen las aplicaciones de Agropark", USUARIO, a)) for a in APLIC_FIFO]
    ins_apl = ("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento,IdMovimientoOrigen,TipoDocumento,IdDocumentoAplicado,ImporteAplicado,Fecha,Usuario,Anulada,Origen,NotaConciliacion) "
               "VALUES (?,?,'CompraDeuda',?,?,SYSDATETIME(),?,0,?,?)")
    nota = "motosierra Diners Lucy (Sergio 25/10/2026)"
    st += [(ins_apl, ("bna", 16500, F728, Decimal("588.00"), USUARIO, "manual", nota)),
           (ins_apl, ("bna", 16501, F765, Decimal("814.00"), USUARIO, "manual", nota)),
           (ins_apl, ("comp-compra", NC020, F829, Decimal("80.59"), USUARIO, "manual", nota))]
    resto = Decimal("13223.00")  # 13.811,00 - anticipo 588
    for n, b in enumerate(bna, 1):
        imp, f = Decimal(str(b["v"])), date.fromisoformat(str(b["f"]))
        st.append(("INSERT INTO dbo.[Pagos efectivo] (IdContacto,IdTipoMovimiento,IdFormaPago,Fecha,Cuenta,Caja,[Numero documento],[Importe imputado],IdOperacion) "
                   "VALUES (?,1,20,?,'White','Particular L',NULL,?,?)", (AGROPARK, f.isoformat(), imp, op)))
        nuevo = "(SELECT MAX(IdPagoEfectivo) FROM dbo.[Pagos efectivo] WHERE IdContacto=%d AND IdOperacion=%d)" % (AGROPARK, op)
        aplica = min(imp, resto)
        resto -= aplica
        if aplica > 0:
            st.append(("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento,IdMovimientoOrigen,TipoDocumento,IdDocumentoAplicado,ImporteAplicado,Fecha,Usuario,Anulada,Origen,NotaConciliacion) "
                       "SELECT 'efectivo'," + nuevo + ",'CompraDeuda',?,?,SYSDATETIME(),?,0,?,?", (F728, aplica, USUARIO, "manual", nota)))
        v = a_fecha(imp, f)
        usd, kg = Decimal(str(v["importeUSD"])), Decimal(str(v["importeKgCarne"]))
        st += [("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario) "
                "SELECT ?,'Devolucion',?,?,?,?,'PagosEfectivo'," + nuevo + ",'Tarjeta Diners Lucy',?,?",
                (LUCY, imp, usd, kg, f.isoformat(), f"Agropark: cuota {n}/6 de la motosierra de Giamigli pagada con la Diners de Lucy (Sergio 25/10/2026).", USUARIO)),
               ("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario) "
                "VALUES (?,'AsignacionGasto',?,?,?,?,'Banco Nacion',?,'Banco Nación',?,?)",
                (LUCY, imp, usd, kg, f.isoformat(), b["i"], f"Giamigli reintegra a Lucy la cuota {n}/6 de la motosierra (transferencia BNA {b['i']}).", USUARIO)),
               ("UPDATE dbo.[Movimientos BNA] SET IdContacto=?, Contacto='Lucy' WHERE IdMovimientoBNA=? AND IdContacto=?", (LUCY_CONTACTO, b["i"], AGROPARK))]
        op += 1
    st.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
               "VALUES (?,'aplicada',?,?,SYSDATETIME(),?,SYSDATETIME(),?,?)",
               (RULE, json.dumps({"bna": BNA, "aplicacionesAnuladas": APLIC_FIFO}), USUARIO, USUARIO, res["backup"],
                f"Motosierra Agropark: 6 cuotas Diners de Lucy ({total}) y reintegros BNA a Lucy; Lucy neto 0, Agropark 0.")))
    execute_write_transaction(st)
    res.update(estado="aplicado", saldoAgroparkDespues=str(_saldo(AGROPARK)))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(ap.parse_args().aplicar), default=str, ensure_ascii=False, indent=1))
