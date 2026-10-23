"""Vínculo documental de tres pagos efectivos existentes; no crea movimientos ni cambia saldos."""

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from src.db.connection import get_connection, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

PARES = [
    (3, 223, "2011-04-04", Decimal("200"), 72),
    (4, 222, "2011-07-06", Decimal("71.78"), 72),
    (29, 581, "2014-05-07", Decimal("104.90"), 315),
]
RULE = "condominio-vinculos-caja-3-4-29-036"


def control(c):
    return {
        "cajas": [
            tuple(r)
            for r in c.execute(
                "SELECT Caja,COUNT_BIG(*),SUM(Importe) FROM dbo.MovimientosCajaEfectivo GROUP BY Caja ORDER BY Caja"
            ).fetchall()
        ],
        "cuentas": [
            tuple(r)
            for r in c.execute(
                "SELECT IdContacto,SUM(Credito-Deuda) FROM dbo.vw_MovimientosCuenta_Base GROUP BY IdContacto ORDER BY IdContacto"
            ).fetchall()
        ],
        "socios": [
            tuple(r)
            for r in c.execute(
                "SELECT IdSocio,COUNT_BIG(*),SUM(Importe),SUM(ImporteUSD),SUM(ImporteKgCarne) FROM dbo.MovimientosCuentaSocio GROUP BY IdSocio ORDER BY IdSocio"
            ).fetchall()
        ],
    }


def run(aplicar=False):
    _assert_target_is_wc()
    with get_connection() as conn:
        c = conn.cursor()
        current = [
            list(
                c.execute(
                    "SELECT IdMovimiento,IdPagoEfectivo,Detalle FROM dbo.MovimientosCajaEfectivo WHERE IdMovimiento=?",
                    m,
                ).fetchone()
            )
            for m, *_ in PARES
        ]
    result = {
        "estado": "inspeccion",
        "pares": PARES,
        "antes": current,
        "nota": "581 conserva organismo315; Impuesto228 / operación1046; rótulo fuenteAFIP preservado.",
    }
    if not aplicar:
        return result
    if all(r[1] == p[1] for r, p in zip(current, PARES, strict=True)):
        return {**result, "estado": "ya_vinculados_sin_escrituras"}
    backup = backup_verificado("condominio_vinculos_tres_036")
    result["backupVerificado"] = backup
    folder = Path(__file__).resolve().parents[2] / "backups" / "condominio-18-pagos-036"
    folder.mkdir(parents=True, exist_ok=True)
    log = folder / f"aplicacion-{datetime.now():%Y%m%d-%H%M%S}.json"

    def save():
        log.write_text(
            json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    result["estado"] = "respaldado"
    save()
    with get_connection(readonly=False) as conn:
        c = conn.cursor()
        try:
            c.execute("SET XACT_ABORT ON; BEGIN TRANSACTION")
            if c.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
                raise RuntimeError("Solo WC")
            before = control(c)
            for mov, pago, fecha, importe, contacto in PARES:
                m = c.execute(
                    "SELECT Caja,Fecha,Importe,IdPagoEfectivo,Anulada FROM dbo.MovimientosCajaEfectivo WITH (UPDLOCK,HOLDLOCK) WHERE IdMovimiento=?",
                    mov,
                ).fetchone()
                p = c.execute(
                    "SELECT Fecha,[Importe imputado],IdContacto,IdFormaPago,Caja,IdOperacion FROM dbo.[Pagos efectivo] WITH (UPDLOCK,HOLDLOCK) WHERE IdPagoEfectivo=?",
                    pago,
                ).fetchone()
                if (
                    not m
                    or not p
                    or m[0] != "GiamigliSA"
                    or str(m[1])[:10] != fecha
                    or m[2] != -importe
                    or m[3] is not None
                    or m[4]
                    or str(p[0])[:10] != fecha
                    or p[1] != importe
                    or p[2] != contacto
                    or p[3] != 3
                    or p[4] != "Condominio"
                ):
                    raise RuntimeError("Cambió evidencia o ya existe vínculo")
                if c.execute(
                    "SELECT 1 FROM dbo.MovimientosCajaEfectivo WITH (UPDLOCK,HOLDLOCK) WHERE IdPagoEfectivo=?",
                    pago,
                ).fetchone():
                    raise RuntimeError("Pago ya vinculado a otra fila")
                if pago == 581:
                    d = c.execute(
                        "SELECT IdOrganismo,Importe,IdOperacion FROM dbo.Impuestos WHERE IdImpuesto=228"
                    ).fetchone()
                    if not d or tuple(d) != (315, importe, 1046) or p[5] != 1046:
                        raise RuntimeError("Cambió respaldo de UATRE")
                note = f"036: vínculo a pago efectivo {pago} del Condominio; fuente Movimientos LSC.xlsx/Movs. Sin nuevo movimiento."
                if pago == 581:
                    note = "036: vínculo pago581. Rótulo original AFIP conservado; organismo UATRE315, aporte sindical abril2014, Impuesto228/operación1046. Sin reasignación fiscal."
                c.execute(
                    "UPDATE dbo.MovimientosCajaEfectivo SET IdPagoEfectivo=?,Detalle=CONCAT(CASE WHEN NULLIF(Detalle,'') IS NULL THEN '' ELSE Detalle+' | ' END,?) WHERE IdMovimiento=? AND IdPagoEfectivo IS NULL",
                    pago,
                    note,
                    mov,
                )
                if c.rowcount != 1:
                    raise RuntimeError("Cambio concurrente")
            after = control(c)
            if before != after:
                raise RuntimeError("Un vínculo documental alteró saldos o cantidades")
            c.execute(
                "INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,?,SYSUTCDATETIME(),?,SYSUTCDATETIME(),?,?)",
                RULE,
                json.dumps({"pares": PARES, "antes": current}, default=str),
                "Codex (Sergio 23/10/2026)",
                "Codex (Sergio 23/10/2026)",
                backup,
                "Tres vínculos documentales de pagos en efectivo; 15 medios no efectivos no se fuerzan a caja. Sin reasignación UATRE/AFIP ni cambios de saldo.",
            )
            c.execute("COMMIT TRANSACTION")
            result.update(estado="aplicado", controlesAntes=before, controlesDespues=after)
        except Exception as exc:
            c.execute("IF @@TRANCOUNT>0 ROLLBACK TRANSACTION")
            result.update(estado="revertido", error=str(exc))
            save()
            raise
    save()
    return {
        "estado": result["estado"],
        "pares": PARES,
        "backupVerificado": backup,
        "informe": str(log),
        "saldosSinCambios": True,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--aplicar", action="store_true")
    print(json.dumps(run(p.parse_args().aplicar), default=str, ensure_ascii=True))
