"""Corrección documental acotada. Inspección por defecto; --aplicar respalda WC.

No modifica pagos ni crea aportes. Conserva original/anterior en auditoría.
"""

import argparse
import hashlib
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.db.connection import _assert_target_is_wc, reconciliation_transaction
from src.db.connection import _reconciliation_connection
from src.features.cajas_efectivo.operaciones import read
from src.features.vinculos.backup import backup_verificado

EASY, COOP = 2143509990, 2143509899
RULE = "condominio-documentos-easy-cooperativa-036"
OUT = Path(__file__).resolve().parents[2] / "backups/condominio-15-medios-036"
VIEWS = ("vw_Cns_Total_Det_Compras", "vw_Compras_ImporteDocumento")


def rows(c, sql, params=()):
    c.execute(sql, params)
    names = [d[0] for d in c.description]
    return [dict(zip(names, r, strict=True)) for r in c.fetchall()]


def state(query):
    return {
        "detalles": query(
            "SELECT * FROM dbo.Det_Compras WHERE IdCompra IN (?,?) ORDER BY IdDetalleCompra",
            (EASY, COOP),
        ),
        "cabeceras": query("SELECT * FROM dbo.Compras WHERE IdDeuda IN (?,?)", (EASY, COOP)),
        "totales": query(
            "SELECT IdDeuda,ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento "
            "WHERE IdDeuda IN (?,?) ORDER BY IdDeuda",
            (EASY, COOP),
        ),
        "aplicaciones": query(
            "SELECT * FROM dbo.AplicacionesPago WHERE IdDocumentoAplicado IN (?,?) "
            "ORDER BY IdAplicacion",
            (EASY, COOP),
        ),
        "fichas": query("SELECT * FROM dbo.RevisionFichas WHERE IdContacto IN (22,29)"),
        "vistas": query(
            "SELECT name,OBJECT_DEFINITION(object_id) definicion FROM sys.views "
            "WHERE name IN ('vw_Cns_Total_Det_Compras','vw_Compras_ImporteDocumento') ORDER BY name"
        ),
    }


def controls(query):
    return {
        "cuentas": query(
            "SELECT IdContacto,SUM(Credito-Deuda) saldo FROM dbo.vw_MovimientosCuenta_Base "
            "GROUP BY IdContacto ORDER BY IdContacto"
        ),
        "cajas": query(
            "SELECT Caja,COUNT_BIG(*) n,SUM(Importe) importe FROM dbo.MovimientosCajaEfectivo "
            "GROUP BY Caja ORDER BY Caja"
        ),
        "socios": query(
            "SELECT IdSocio,COUNT_BIG(*) n,SUM(Importe) importe,SUM(ImporteUSD) usd,"
            "SUM(ImporteKgCarne) kg FROM dbo.MovimientosCuentaSocio GROUP BY IdSocio ORDER BY "
            "IdSocio"
        ),
        "pagos": query(
            "SELECT COUNT_BIG(*) n,SUM([Importe imputado]) importe FROM dbo.[Pagos efectivo]"
        ),
    }


def run(aplicar=False):
    _assert_target_is_wc()
    before = state(read)
    if read(
        "SELECT 1 x FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,)
    ):
        assert {r["IdDeuda"]: round(r["ImporteDocumento"], 2) for r in before["totales"]} == {
            EASY: Decimal("1361.54"),
            COOP: Decimal("2253.03"),
        }
        return {"estado": "ya_aplicado_sin_escrituras", "totales": before["totales"]}
    easy = [r for r in before["detalles"] if r["IdCompra"] == EASY]
    assert len(easy) == 15
    byid = {r["IdDetalleCompra"]: r for r in easy}
    assert byid[2141364618]["Precio Unitario"] == 67.5
    assert byid[2141364624]["Cantidad"] == 3
    assert byid[2141364624]["Precio Unitario"] == 92.56
    assert (
        read(
            "SELECT COLUMNPROPERTY(OBJECT_ID('dbo.Det_Compras'),'IdDetalleCompra','IsIdentity') x"
        )[0]["x"]
        == 1
    )
    roots = Path("C:/Users/Sergio/Documents/La Herencia/Comprobantes/Giamigli")
    files = [
        roots / "2014/20140307_Easy.pdf",
        roots / "2013/20131205_CooperativaAgropecuaria 001.pdf",
    ]
    result = {
        "estado": "inspeccion",
        "antes": before,
        "fuentes": [
            {"ruta": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files
        ],
        "objetivo": {"Easy": "1361.54", "Cooperativa": "2253.03"},
    }
    if not aplicar:
        return {
            "estado": "inspeccion",
            "totales": before["totales"],
            "objetivo": result["objetivo"],
        }
    result["backupVerificado"] = backup_verificado("condominio_documentos_easy_coop_036")
    OUT.mkdir(parents=True, exist_ok=True)
    log = OUT / f"correccion-documentos-{datetime.now():%Y%m%d-%H%M%S}.json"

    def save():
        log.write_text(
            json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    save()
    try:
        with reconciliation_transaction():
            c = _reconciliation_connection.get().cursor()

            def query(sql, params=()):
                return rows(c, sql, params)

            if state(query) != before:
                raise RuntimeError("Cambió el estado desde la inspección")
            original_control = controls(query)
            # Conversión a float doble antes del IVA: evita el coeficiente real simple.
            for v in before["vistas"]:
                definition = v["definicion"]
                assert definition.count("/* precision fletes036 */") == 1
                alias = "cfx" if v["name"] == "vw_Compras_ImporteDocumento" else "c"
                marker = "/* precision fletes036 */"
                replacement = (
                    f"{marker} OR {alias}.IdDeuda IN ({EASY},{COOP}) /* fiscal Condominio036 */"
                )
                definition = definition.replace(marker, replacement)
                detail = "dc" if alias == "cfx" else "d"
                old_case = f"CASE WHEN {detail}.IdCompra=2143514851"
                assert definition.count(old_case) == 1
                fiscal = (
                    f"CASE WHEN {detail}.IdCompra={COOP} THEN SUM("
                    f"CONVERT(float,{detail}.Cantidad)*{detail}.[Precio Unitario] + "
                    f"ROUND(CONVERT(float,{detail}.Cantidad)*{detail}.[Precio Unitario]*"
                    f"CONVERT(float,{detail}.IVA)/100.0,2)) "
                    f"/* IVA por alicuota original036 */ WHEN {detail}.IdCompra=2143514851"
                )
                c.execute(
                    definition.replace(old_case, fiscal).replace("CREATE VIEW", "ALTER VIEW", 1)
                )
            c.execute(
                "UPDATE dbo.Det_Compras SET [Precio Unitario]=65.70 WHERE "
                "IdDetalleCompra=2141364618"
            )
            c.execute("UPDATE dbo.Det_Compras SET Cantidad=2 WHERE IdDetalleCompra=2141364624")
            # Copia reparto General/No Aplica del propio documento, sin inferir campaña productiva.
            fields = (
                "IdCompra,Cantidad,[Producto/Servicio],IdFormulado,IdCentroCostos,IdDestino,"
                "IdRubro,[IdCampaña],[Campaña],[Precio Unitario],IVA,[Ajuste financiero]"
            )
            c.execute(
                f"INSERT INTO dbo.Det_Compras ({fields}) "
                "SELECT IdCompra,1,[Producto/Servicio],IdFormulado,IdCentroCostos,IdDestino,"
                "IdRubro,[IdCampaña],[Campaña],92.57,IVA,[Ajuste financiero] "
                "FROM dbo.Det_Compras WHERE IdDetalleCompra=2141364624"
            )
            c.execute(
                f"INSERT INTO dbo.Det_Compras ({fields}) "
                "SELECT IdCompra,4,'AMP HALOGENA BARRA',0,IdCentroCostos,IdDestino,"
                "5,[IdCampaña],[Campaña],16.4875,21,0 FROM dbo.Det_Compras "
                "WHERE IdDetalleCompra=2141364631"
            )
            c.execute("UPDATE dbo.Compras SET PercepcionIVA=32.94 WHERE IdDeuda=?", EASY)
            # El origen tarjetas217 hoy es un peaje2022 de272, no este pago2014.
            bad = query("SELECT * FROM dbo.AplicacionesPago WHERE IdAplicacion=8568")
            assert len(bad) == 1 and not bad[0]["Anulada"]
            assert bad[0]["IdDocumentoAplicado"] == EASY
            assert bad[0]["IdMovimientoOrigen"] == 217 and bad[0]["OrigenMovimiento"] == "tarjetas"
            assert query(
                "SELECT IdCompra,ImporteImputado FROM dbo.Tarjetas_Resumenes_Lineas_Compras "
                "WHERE IdVinculo=217"
            )[0] == {"IdCompra": 2143513885, "ImporteImputado": Decimal("272")}
            p = query(
                "SELECT IdOperacion,IdContacto,[Importe imputado] importe FROM dbo.[Pagos "
                "efectivo] WHERE IdPagoEfectivo=561"
            )[0]
            assert p == {"IdOperacion": 995, "IdContacto": 29, "importe": Decimal("1250.97")}
            assert not query(
                "SELECT 1 x FROM dbo.AplicacionesPago WHERE OrigenMovimiento='efectivo' AND "
                "IdMovimientoOrigen=561 AND Anulada=0"
            )
            c.execute(
                "UPDATE dbo.AplicacionesPago SET Anulada=1,MotivoAnulacion=?,"
                "UsuarioAnulacion='Codex036',FechaAnulacion=SYSDATETIME() WHERE IdAplicacion=8568",
                "Origen tarjetas217 pertenece a peaje2022; reemplazada por pago561/op995.",
            )
            c.execute(
                "INSERT INTO dbo.AplicacionesPago "
                "(OrigenMovimiento,IdMovimientoOrigen,TipoDocumento,"
                "IdDocumentoAplicado,ImporteAplicado,Fecha,Usuario,Anulada,"
                "Origen,NotaConciliacion) "
                "VALUES ('efectivo',561,'CompraDeuda',?,1250.97,SYSDATETIME(),'Codex036',0,"
                "'manual','Pago561/op995; importe existente parcial. Falta "
                "titular/resumen VISA.')",
                EASY,
            )
            c.execute(
                "UPDATE dbo.RevisionFichas SET Estado='esperando-evidencia',Nota=CONCAT(Nota,?),"
                "UsuarioActualiza='Codex036',FechaActualiza=SYSDATETIME() WHERE IdContacto IN "
                "(22,29)",
                " | 24/10/2026: revisión puntual Condominio; originales Easy1361.54/Coop2253.03. "
                "Sin pago nuevo. Falta titular/resumen y conciliación del importe pagado. Ver "
                "informe036.",
            )
            after = state(query)
            totals = {r["IdDeuda"]: round(r["ImporteDocumento"], 2) for r in after["totales"]}
            assert totals == {EASY: Decimal("1361.54"), COOP: Decimal("2253.03")}, totals
            after_control = controls(query)
            for k in ("cajas", "socios", "pagos"):
                assert original_control[k] == after_control[k], k
            old_balances = {r["IdContacto"]: r["saldo"] for r in original_control["cuentas"]}
            new_balances = {r["IdContacto"]: r["saldo"] for r in after_control["cuentas"]}
            assert {k: v for k, v in old_balances.items() if k not in (22, 29)} == {
                k: v for k, v in new_balances.items() if k not in (22, 29)
            }
            for doc, contact in ((EASY, 29), (COOP, 22)):
                old = next(r["ImporteDocumento"] for r in before["totales"] if r["IdDeuda"] == doc)
                new = next(r["ImporteDocumento"] for r in after["totales"] if r["IdDeuda"] == doc)
                assert new_balances[contact] - old_balances[contact] == old - new
            result.update(
                despues=after, controlesAntes=original_control, controlesDespues=after_control
            )
            c.execute(
                "INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,"
                "UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,"
                "'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)",
                RULE,
                json.dumps({"informe": str(log), "documentos": [EASY, COOP]}),
                result["backupVerificado"],
                "Originales Easy/Coop corregidos; vínculo8568 anulado y reemplazado por561; "
                "sin pagos nuevos.",
            )
        result["estado"] = "aplicado"
    except Exception as exc:
        result.update(estado="revertido", error=str(exc))
        save()
        raise
    save()
    from src.features.auditoria_cuentas.bimonetaria import invalidar
    from src.features.revision_cuentas.cache import invalidar as invalidar_revision

    invalidar()
    invalidar_revision()
    return {
        "estado": result["estado"],
        "informe": str(log),
        "totales": after["totales"],
        "backup": result["backupVerificado"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=False))
