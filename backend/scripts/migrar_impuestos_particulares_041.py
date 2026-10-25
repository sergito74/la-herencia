"""041: esquema de impuestos particulares y migración del caso 3206.

Sin argumentos solo inspecciona. `--esquema` crea las tres tablas (aditivo, idempotente). `--aplicar` además migra el
impuesto 3206 (Inmobiliario Complementario 3/2017 del Condominio): crea la carga vinculada, reemplaza el Debe manual y
vincula el Haber de la devolución de Lucy. Respaldo COPY_ONLY verificado antes de escribir; nunca toca dbo.Impuestos,
LaHerencia ni Access. Repetir no escribe nada.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.db.connection import _assert_target_is_wc, fetch_all, fetch_one, get_connection

TABLAS = {
    "ImpuestosParticulares": """
        IdCarga int IDENTITY PRIMARY KEY,
        IdImpuesto int NOT NULL REFERENCES dbo.Impuestos(IdImpuesto),
        IdSocio int NOT NULL REFERENCES dbo.Socios(IdSocio),
        Importe decimal(18,2) NOT NULL CHECK (Importe > 0),
        Motivo nvarchar(255) NOT NULL CHECK (LEN(LTRIM(RTRIM(Motivo))) > 0),
        Partida nvarchar(60) NULL,
        TitularOscar bit NOT NULL DEFAULT 0,
        IdMovimientoSocio int NOT NULL REFERENCES dbo.MovimientosCuentaSocio(IdMovimiento),
        Estado varchar(10) NOT NULL DEFAULT 'vigente' CHECK (Estado IN ('vigente','anulada')),
        ClaveIdempotencia uniqueidentifier NOT NULL UNIQUE,
        HuellaSolicitud char(64) NOT NULL,
        CreadoPor nvarchar(60) NOT NULL,
        CreadoEn datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
        MotivoAnulacion nvarchar(255) NULL,
        AnuladoPor nvarchar(60) NULL,
        AnuladoEn datetime2 NULL,
        CONSTRAINT CK_ImpPart_Oscar CHECK (TitularOscar = 0 OR (IdSocio = 3 AND Partida IS NOT NULL))""",
    "ImpuestosParticularesDevoluciones": """
        IdVinculo int IDENTITY PRIMARY KEY,
        IdCarga int NOT NULL REFERENCES dbo.ImpuestosParticulares(IdCarga),
        IdMovimientoSocio int NOT NULL REFERENCES dbo.MovimientosCuentaSocio(IdMovimiento),
        Importe decimal(18,2) NOT NULL CHECK (Importe > 0),
        Estado varchar(10) NOT NULL DEFAULT 'vigente' CHECK (Estado IN ('vigente','anulada')),
        ClaveIdempotencia uniqueidentifier NOT NULL UNIQUE,
        HuellaSolicitud char(64) NOT NULL,
        Usuario nvarchar(60) NOT NULL,
        Fecha datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
        MotivoAnulacion nvarchar(255) NULL,
        AnuladoPor nvarchar(60) NULL,
        AnuladoEn datetime2 NULL""",
    "PartidasTitulares": """
        Partida nvarchar(60) NOT NULL PRIMARY KEY,
        IdSocio int NULL,
        IdCargaOrigen int NULL,
        Estado varchar(12) NOT NULL CHECK (Estado IN ('vigente','ambigua','sin_cargas')),
        TitularOscar bit NOT NULL DEFAULT 0,
        Fecha datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
        Usuario nvarchar(60) NOT NULL""",
}
INDICES = [
    "CREATE INDEX IX_ImpPart_Impuesto ON dbo.ImpuestosParticulares(IdImpuesto, Estado)",
    "CREATE UNIQUE INDEX UX_ImpPartDev_ParVigente ON dbo.ImpuestosParticularesDevoluciones(IdCarga, IdMovimientoSocio) "
    "WHERE Estado = 'vigente'",
    "CREATE INDEX IX_ImpPartDev_Movimiento ON dbo.ImpuestosParticularesDevoluciones(IdMovimientoSocio, Estado)",
]
OUT = Path(__file__).resolve().parents[2] / "backups" / "impuestos-particulares-041"

# Caso 3206 (spec FR-014). Valores verificados en lectura (validacion.md); la inspección los vuelve a comprobar.
CASO = {"impuesto": 3206, "socio": 3, "importe": Decimal("8852.10"), "debeManual": 3149, "haber": 3150,
        "clave": "4f1d2c00-0041-4320-8000-000000003206", "claveVinculo": "4f1d2c00-0041-4320-8000-000000003150",
        "motivo": "Inmobiliario Complementario 3/2017 del Condominio (lo pagan los 3 socios; Sergio 25/10/2026)",
        "usuario": "migracion-041"}


def _faltantes() -> list[str]:
    existentes = {r["name"] for r in fetch_all("SELECT name FROM sys.tables")}
    return [t for t in TABLAS if t not in existentes]


def crear_esquema() -> list[str]:
    """DDL aditivo en una transacción. Devuelve las tablas creadas."""
    _assert_target_is_wc()
    faltan = _faltantes()
    with get_connection(readonly=False) as conn:
        c = conn.cursor()
        if c.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        c.execute("BEGIN TRANSACTION")
        try:
            for t in TABLAS:
                if t in faltan:
                    c.execute(f"CREATE TABLE dbo.{t} ({TABLAS[t]})")
            for ddl in INDICES:
                nombre = ddl.split(" INDEX ")[1].split(" ")[0]
                if not c.execute("SELECT 1 FROM sys.indexes WHERE name=?", nombre).fetchone():
                    c.execute(ddl)
            c.execute("COMMIT TRANSACTION")
        except Exception:
            c.execute("IF @@TRANCOUNT>0 ROLLBACK TRANSACTION")
            raise
    return faltan


def inspeccion_3206() -> dict:
    imp = fetch_one("SELECT IdImpuesto, CONVERT(varchar(10),Fecha,23) fecha, CAST(Importe AS decimal(18,2)) importe FROM dbo.Impuestos "
                    "WHERE IdImpuesto=?", (CASO["impuesto"],))
    movs = {r["IdMovimiento"]: r for r in fetch_all(
        "SELECT IdMovimiento, IdSocio, Tipo, CAST(Importe AS decimal(18,2)) Importe, CONVERT(varchar(10),Fecha,23) Fecha, "
        "Origen, Anulada, CAST(ImporteUSD AS decimal(18,4)) ImporteUSD, CAST(ImporteKgCarne AS decimal(18,3)) ImporteKgCarne "
        "FROM dbo.MovimientosCuentaSocio WHERE IdMovimiento IN (?,?)", (CASO["debeManual"], CASO["haber"]))}
    debe, haber = movs.get(CASO["debeManual"]), movs.get(CASO["haber"])
    problemas = []
    if not imp or Decimal(str(imp["importe"])) != CASO["importe"] or imp["fecha"] != "2017-11-07":
        problemas.append(f"Impuesto 3206 distinto de lo esperado: {imp}")
    if not debe or debe["Tipo"] != "AsignacionGasto" or debe["IdSocio"] != 3 or Decimal(str(debe["Importe"])) != CASO["importe"] \
            or debe["Fecha"] != "2017-11-07" or debe["Origen"] not in (None, "Manual"):
        problemas.append(f"Debe manual 3149 distinto de lo esperado: {debe}")
    if not haber or haber["Tipo"] != "Devolucion" or haber["IdSocio"] != 3 or Decimal(str(haber["Importe"])) != CASO["importe"] \
            or haber["Fecha"] != "2017-11-13" or haber["Anulada"]:
        problemas.append(f"Haber 3150 distinto de lo esperado: {haber}")
    ya = fetch_all("SELECT IdCarga, Estado FROM dbo.ImpuestosParticulares WHERE ClaveIdempotencia=?", (CASO["clave"],)) \
        if "ImpuestosParticulares" not in _faltantes() else []
    return {"impuesto": imp, "debeManual": debe, "haber": haber, "problemas": problemas, "migrado": bool(ya)}


def migrar_3206() -> dict:
    from src.features.impuestos import particular

    insp = inspeccion_3206()
    if insp["migrado"]:
        return {"estado": "ya_migrado_sin_escrituras"}
    if insp["problemas"]:
        raise RuntimeError("; ".join(insp["problemas"]))
    if insp["debeManual"]["Anulada"]:
        raise RuntimeError("El Debe manual 3149 ya está anulado: revisar antes de migrar")
    socio_antes = particular.saldo_socio(CASO["socio"])
    carga, _ = particular.tx_crear_carga(CASO["impuesto"], {
        "claveIdempotencia": CASO["clave"], "idSocio": CASO["socio"], "importe": str(CASO["importe"]), "motivo": CASO["motivo"],
        "partida": None, "titularOscar": False, "reemplazarMovimientoManual": CASO["debeManual"], "confirmarCuentaCerrada": True,
    }, CASO["usuario"])
    vinculo, _ = particular.tx_vincular(carga["idCarga"], {
        "claveIdempotencia": CASO["claveVinculo"], "idMovimientoSocio": CASO["haber"], "importe": str(CASO["importe"]),
    }, CASO["usuario"])
    socio_despues = particular.saldo_socio(CASO["socio"])
    if socio_antes != socio_despues:
        raise RuntimeError(f"Cambió el saldo del Condominio: {socio_antes} -> {socio_despues}")
    return {"estado": "aplicado", "carga": carga, "vinculo": vinculo, "saldoCondominio": socio_despues}


def run(esquema=False, aplicar=False):
    _assert_target_is_wc()
    res = {"tablasFaltantes": _faltantes()}
    if not (esquema or aplicar):
        res["caso3206"] = inspeccion_3206()
        return res
    from src.features.vinculos.backup import backup_verificado

    OUT.mkdir(parents=True, exist_ok=True)
    res["backup"] = backup_verificado("impuestos_particulares_041")
    res["tablasCreadas"] = crear_esquema()
    if aplicar:
        res["caso3206"] = migrar_3206()
    (OUT / f"migracion-{datetime.now():%Y%m%d-%H%M%S}.json").write_text(json.dumps(res, default=str, ensure_ascii=False, indent=2),
                                                                         encoding="utf-8")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--esquema", action="store_true")
    ap.add_argument("--aplicar", action="store_true")
    a = ap.parse_args()
    print(json.dumps(run(a.esquema, a.aplicar), default=str, ensure_ascii=False, indent=1))
