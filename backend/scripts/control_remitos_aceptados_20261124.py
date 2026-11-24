"""Marca «revisado y aceptado» del control de remitos (24/11/2026, Sergio: las excepciones van en los datos, no en el
código). Crea dbo.ControlRemitosAceptados y pasa ahí las excepciones que estaban fijas en control_cierre.py.
Idempotente. Uso (desde backend/): python -m scripts.control_remitos_aceptados_20261124 [--aplicar]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import fetch_all, get_connection  # noqa: E402

TABLA = """IF OBJECT_ID('dbo.ControlRemitosAceptados') IS NULL
CREATE TABLE dbo.ControlRemitosAceptados (
    IdAceptado int IDENTITY(1,1) NOT NULL CONSTRAINT PK_ControlRemitosAceptados PRIMARY KEY,
    Tipo nvarchar(20) NOT NULL CONSTRAINT CK_ControlRemitosAceptados_Tipo CHECK (Tipo IN ('sin_factura', 'vinculo')),
    IdRemito int NOT NULL,
    IdDetalleRemito int NULL,
    IdCompra int NULL,
    Motivo nvarchar(300) NOT NULL,
    Usuario nvarchar(60) NULL,
    Fecha datetime2 NOT NULL CONSTRAINT DF_ControlRemitosAceptados_Fecha DEFAULT SYSDATETIME(),
    Vigente bit NOT NULL CONSTRAINT DF_ControlRemitosAceptados_Vigente DEFAULT 1
)"""

# (tipo, IdRemito, IdDetalleRemito, IdCompra, motivo) — decisiones de Sergio del 21 y 24/11/2026.
INICIALES = [
    ("sin_factura", 80, 163, None, "Tordon 24K 5 L Lartirigoyen 22/11/2019: quedó sin facturar (Sergio 24/11/2026)"),
    ("sin_factura", 116, 239, None, "Betito 300 kg Yanquelen 30/11/2020: lo mandó Yanquelen y no lo facturó (Sergio 24/11/2026)"),
    ("sin_factura", 162, 371, None, "Calén INTA 2.058 kg Yanquelen 24/05/2023: desde San Emilio, nunca facturada (Sergio 24/11/2026)"),
    ("vinculo", 126, None, 2143513222, "Emerge y Rocío comprados a Tierras de Henderson, entregados con remito de Sunanco (Sergio 24/11/2026)"),
    ("vinculo", 121, None, 2143513221, "Dividend Extra de Syngenta facturado por Sunanco (Sergio 24/11/2026)"),
    ("vinculo", 121, None, 2143513222, "Power Plus II de Syngenta facturado por Tierras de Henderson (Sergio 24/11/2026)"),
    ("vinculo", 82, None, 2143512373, "Betito 2019 = semilla propia valorizada por la clasificación de Garnica (Sergio 24/11/2026)"),
    ("sin_costo", None, None, None, "Flumeyt +: única entrada histórica sin factura, ya consumida (Sergio 21/11/2026)"),
    ("vinculo", 200, None, 2143517472, "LT725TRE facturado y anulado por NC 0020-00135455, devolución en el mismo remito (Sergio 24/11/2026)"),
]


def main():
    aplicar = "--aplicar" in sys.argv
    print(f"Marcas iniciales: {len(INICIALES)}")
    if not aplicar:
        print("Simulación (usar --aplicar)")
        return
    with get_connection(readonly=False) as cn:
        cn.autocommit = False
        cur = cn.cursor()
        try:
            cur.execute(TABLA)
            # Marca por producto: consumo sin costo aceptado (entrada sin remito, ej. stock inicial).
            cur.execute("IF COL_LENGTH('dbo.ControlRemitosAceptados', 'IdProducto') IS NULL "
                        "ALTER TABLE dbo.ControlRemitosAceptados ADD IdProducto int NULL")
            cur.execute("ALTER TABLE dbo.ControlRemitosAceptados ALTER COLUMN IdRemito int NULL")
            cur.execute("ALTER TABLE dbo.ControlRemitosAceptados DROP CONSTRAINT CK_ControlRemitosAceptados_Tipo")
            cur.execute("ALTER TABLE dbo.ControlRemitosAceptados ADD CONSTRAINT CK_ControlRemitosAceptados_Tipo "
                        "CHECK (Tipo IN ('sin_factura', 'vinculo', 'sin_costo'))")
            cur.execute("IF NOT EXISTS (SELECT 1 FROM dbo.ControlRemitosAceptados WHERE Tipo = 'sin_costo' AND IdProducto = 40958 "
                        "AND Vigente = 1) INSERT INTO dbo.ControlRemitosAceptados (Tipo, IdProducto, Motivo, Usuario) VALUES "
                        "('sin_costo', 40958, 'Flumeyt +: única entrada histórica sin factura, ya consumida (Sergio 21/11/2026)', 'sergio')")
            for tipo, r, d, c, m in INICIALES:
                if tipo == "sin_costo":
                    continue
                cur.execute(
                    "IF NOT EXISTS (SELECT 1 FROM dbo.ControlRemitosAceptados WHERE Tipo = ? AND IdRemito = ? "
                    "AND ISNULL(IdDetalleRemito, 0) = ISNULL(?, 0) AND ISNULL(IdCompra, 0) = ISNULL(?, 0) AND Vigente = 1) "
                    "INSERT INTO dbo.ControlRemitosAceptados (Tipo, IdRemito, IdDetalleRemito, IdCompra, Motivo, Usuario) "
                    "VALUES (?, ?, ?, ?, ?, 'sergio')", tipo, r, d, c, tipo, r, d, c, m)
            cn.commit()
        except Exception:
            cn.rollback()
            raise
    print(fetch_all("SELECT COUNT(*) AS n FROM dbo.ControlRemitosAceptados WHERE Vigente = 1"))


if __name__ == "__main__":
    main()
