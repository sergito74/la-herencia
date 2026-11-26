"""052 T026: reservas forrajeras = silos de maíz picado ya cargados en el sistema (factura del contratista de confección).

Sergio 26/11/2026: el silo es reserva y se consume cuando se necesita (sin regla fija). No lleva registro de rollos ni
silos y no hay datos de consumo de ejercicios pasados. Del último silo (Maíz 2024/2025, El Miralejo) se consumió ~20 %
al día de hoy.
- GanReserva: una por silo, Fecha = factura de confección; Kg y costo quedan NULL (el costo sale vivo del Resultado
  por cultivo, no se copia).
- GanReservaConsumo: Kg o Porcentaje (los silos no tienen kg medidos).
Las tablas ya existían vacías (ganaderia_tablas_20261125); se relajan Kg/Costo a NULL y se agrega Porcentaje.
Idempotente. Simula por defecto; con --aplicar hace BACKUP verificado y aplica en una transacción.
Uso (desde backend/): python -m scripts.ganaderia_reservas_silo_20261126 [--aplicar]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ganaderia_tablas_20261125 import _backup  # noqa: E402
from src.db.connection import get_connection  # noqa: E402

MAIZ = 1
SILOS = [  # campaña, fecha de la factura de confección, contratista, ha
    ("2016/2017", "2017-07-24", "Aisemberg", 7), ("2018/2019", "2019-03-18", "Aisemberg", 6.2),
    ("2019/2020", "2020-04-27", "Aisemberg", 12.2), ("2021/2022", "2022-03-22", "Aisemberg", 9.3),
    ("2022/2023", "2023-02-28", "Muñoz", 10.2), ("2024/2025", "2025-02-13", "El Miralejo", 6)]
CONSUMO = ("2024/2025", "2026-11-26", 20, "Sergio 26/11/2026: al día de hoy se consumió aproximadamente el 20 %")


def _ck(cur, tabla, nombre, expr):
    if cur.execute("SELECT 1 FROM sys.check_constraints WHERE name = ?", (nombre,)).fetchone():
        cur.execute(f"ALTER TABLE dbo.{tabla} DROP CONSTRAINT {nombre}")
    cur.execute(f"ALTER TABLE dbo.{tabla} ADD CONSTRAINT {nombre} CHECK ({expr})")


def esquema(cur) -> None:
    cur.execute("ALTER TABLE dbo.GanReserva ALTER COLUMN Kg decimal(14,1) NULL")
    cur.execute("ALTER TABLE dbo.GanReserva ALTER COLUMN CostoPesos decimal(16,2) NULL")
    _ck(cur, "GanReserva", "CK_GanReserva_Kg", "Kg IS NULL OR Kg > 0")
    cur.execute("ALTER TABLE dbo.GanReservaConsumo ALTER COLUMN Kg decimal(14,1) NULL")
    if cur.execute("SELECT COL_LENGTH('dbo.GanReservaConsumo','Porcentaje')").fetchone()[0] is None:
        cur.execute("ALTER TABLE dbo.GanReservaConsumo ADD Porcentaje decimal(6,2) NULL")
    _ck(cur, "GanReservaConsumo", "CK_GanResCons_Kg",
        "(Kg IS NOT NULL AND Kg > 0) OR (Porcentaje IS NOT NULL AND Porcentaje > 0 AND Porcentaje <= 100)")


def main(aplicar: bool) -> None:
    if aplicar:
        print("Backup:", _backup())
    with get_connection() as conn:
        cur = conn.cursor()
        if cur.execute("SELECT DB_NAME()").fetchone()[0] != "WC":
            raise RuntimeError("Solo WC")
        esquema(cur)
        ids = {}
        for camp, fecha, quien, ha in SILOS:
            idcamp = cur.execute("SELECT IdCampaña FROM dbo.Campañas WHERE Campaña = ?", (camp,)).fetchone()[0]
            r = cur.execute("SELECT IdReserva FROM dbo.GanReserva WHERE Tipo='Silo' AND IdCultivo=? AND IdCampania=? "
                            "AND Anulado=0", (MAIZ, idcamp)).fetchone()
            if not r:
                cur.execute("INSERT INTO dbo.GanReserva (Tipo, Fecha, IdCultivo, IdCampania, Fuente, Observaciones, CreadoPor) "
                            "OUTPUT INSERTED.IdReserva VALUES ('Silo', ?, ?, ?, ?, ?, 'Claude (052)')",
                            (fecha, MAIZ, idcamp, f"Factura de confección {quien}", f"{ha} ha picadas"))
                r = cur.fetchone()
            ids[camp] = r[0]
        camp, fecha, pct, motivo = CONSUMO
        if not cur.execute("SELECT 1 FROM dbo.GanReservaConsumo WHERE IdReserva=? AND Anulado=0", (ids[camp],)).fetchone():
            cur.execute("INSERT INTO dbo.GanReservaConsumo (IdReserva, Fecha, Porcentaje, Motivo, Usuario) "
                        "VALUES (?, ?, ?, ?, 'Claude (052)')", (ids[camp], fecha, pct, motivo))
        for t in ("GanReserva", "GanReservaConsumo"):
            for row in cur.execute(f"SELECT * FROM dbo.{t}").fetchall():
                print(t, tuple(row))
        conn.commit() if aplicar else conn.rollback()
        print("APLICADO" if aplicar else "SIMULACIÓN (rollback)")


if __name__ == "__main__":
    main("--aplicar" in sys.argv)
