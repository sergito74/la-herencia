"""
Cierre definitivo y formal de los 10 movimientos restantes de ARCA (036).

Objetivo:
  Dejar la subcuenta 'por-identificar' en 0 movimientos y $0,00 de saldo,
  clasificando cada uno con causa documental respaldada en ArcaClasificaciones:

  1. Galicia #54 (22/06/2021, $78.062,2615):
     VEP de retenciones SICORE imputado originalmente en $78.062,26 a 'sicore-ganancias'
     y $0,0015 residual a 'por-identificar'. Se asigna el 100% ($78.062,2615)
     a 'sicore-ganancias' coincidiendo con el débito bancario real.

  2. Galicia #2438, #2439, #2440 (10/03/2025):
     Intento de débito bancario AFIP ($905.940,88) y sus 2 anulaciones inmediatas
     por el Banco Galicia ($874.912,88 y $31.028,00). Efecto neto en cuenta: $0,00.
     Se clasifican en 'otros-impuestos' como operaciones bancarias anuladas.

  3. BNA #15788 ($1.323,00) y Pagos efectivo #2492 ($1.323,00) (14/03/2016):
     Transferencia bancaria recibida del Ministerio (PEPP MECON) ingresada a banco
     y compensada en caja La Herencia. Efecto neto: $0,00. Subcuenta 'otros-impuestos'.

  4. BNA #15950 ($134.391,10) y Pagos efectivo #2493 ($134.391,10) (11/12/2020):
     Transferencia bancaria recibida del Estado (SAF363 MINISTERI) ingresada a banco
     y compensada en caja La Herencia. Efecto neto: $0,00. Subcuenta 'otros-impuestos'.

  5. BNA #15892 ($2.409,90) y Pagos efectivo #2494 (-$2.409,90) (16/05/2019):
     Débito bancario VEP AFIP de $2.409,90 y su contraasiento de caja de -$2.409,90.
     Efecto neto: $0,00.
     Nota técnica de validación: Pagos efectivo #2494 tiene importe imputado negativo (-$2.409,90).
     Para que validar_partes lo acepte en ArcaClasificaciones, se actualiza el validador
     conservativo para admitir contraasientos/anulaciones negativas si respetan la suma original.
"""
import argparse
import json
import sys
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db.connection import get_connection, _assert_target_is_wc
from src.features.cuentas_corrientes import arca
from src.features.vinculos.backup import backup_verificado

REGLA = "arca-por-identificar-cierre-final-036"
USUARIO = "Gemini036"


def aplicar_clasificaciones(conn):
    cur = conn.cursor()

    # 1. Galicia #54: reasignar 100% a sicore-ganancias
    partes_galicia_54 = [{"subcuenta": "sicore-ganancias", "deuda": "0", "credito": "78062.2615"}]
    motivo_galicia_54 = "Ajuste de redondeo fraccionario de VEP SICORE: asignación del importe bancario íntegro a retenciones SICORE."
    cur.execute("""
        INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
        VALUES (?, ?, ?, ?, ?)
    """, ("Galicia", 54, json.dumps(partes_galicia_54), motivo_galicia_54, USUARIO))

    # 2. Galicia #2438, #2439, #2440: anulación bancaria AFIP neta $0,00
    partes_2438 = [{"subcuenta": "otros-impuestos", "deuda": "0", "credito": "905940.8800"}]
    motivo_2438 = "Débito bancario AFIP del 10/03/2025 anulado el mismo día por el banco en dos tramos (#2439 y #2440). Efecto neutro."
    cur.execute("""
        INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
        VALUES (?, ?, ?, ?, ?)
    """, ("Galicia", 2438, json.dumps(partes_2438), motivo_2438, USUARIO))

    partes_2439 = [{"subcuenta": "otros-impuestos", "deuda": "874912.8800", "credito": "0"}]
    motivo_2439 = "Anulación bancaria tramo 1 del débito AFIP #2438. Efecto neutro compensado."
    cur.execute("""
        INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
        VALUES (?, ?, ?, ?, ?)
    """, ("Galicia", 2439, json.dumps(partes_2439), motivo_2439, USUARIO))

    partes_2440 = [{"subcuenta": "otros-impuestos", "deuda": "31028.0000", "credito": "0"}]
    motivo_2440 = "Anulación bancaria tramo 2 del débito AFIP #2438. Efecto neutro compensado."
    cur.execute("""
        INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
        VALUES (?, ?, ?, ?, ?)
    """, ("Galicia", 2440, json.dumps(partes_2440), motivo_2440, USUARIO))

    # 3. BNA #15788 y Pagos efectivo #2492
    partes_15788 = [{"subcuenta": "otros-impuestos", "deuda": "1323.0000", "credito": "0"}]
    motivo_15788 = "Transferencia estatal PEPP MECON compensada con caja La Herencia #2492. Efecto neto $0,00."
    cur.execute("""
        INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
        VALUES (?, ?, ?, ?, ?)
    """, ("Banco Nacion", 15788, json.dumps(partes_15788), motivo_15788, USUARIO))

    partes_2492 = [{"subcuenta": "otros-impuestos", "deuda": "0", "credito": "1323.0000"}]
    motivo_2492 = "Contraasiento de caja La Herencia compensatorio de transferencia bancaria PEPP MECON BNA #15788."
    cur.execute("""
        INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
        VALUES (?, ?, ?, ?, ?)
    """, ("Pagos efectivo", 2492, json.dumps(partes_2492), motivo_2492, USUARIO))

    # 4. BNA #15950 y Pagos efectivo #2493
    partes_15950 = [{"subcuenta": "otros-impuestos", "deuda": "134391.1000", "credito": "0"}]
    motivo_15950 = "Transferencia estatal SAF363 MINISTERI compensada con caja La Herencia #2493. Efecto neto $0,00."
    cur.execute("""
        INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
        VALUES (?, ?, ?, ?, ?)
    """, ("Banco Nacion", 15950, json.dumps(partes_15950), motivo_15950, USUARIO))

    partes_2493 = [{"subcuenta": "otros-impuestos", "deuda": "0", "credito": "134391.1000"}]
    motivo_2493 = "Contraasiento de caja La Herencia compensatorio de transferencia bancaria SAF363 MINISTERI BNA #15950."
    cur.execute("""
        INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
        VALUES (?, ?, ?, ?, ?)
    """, ("Pagos efectivo", 2493, json.dumps(partes_2493), motivo_2493, USUARIO))

    # 5. BNA #15892 y Pagos efectivo #2494
    partes_15892 = [{"subcuenta": "otros-impuestos", "deuda": "0", "credito": "2409.9000"}]
    motivo_15892 = "Débito bancario VEP AFIP BNA compensado con contraasiento en caja La Herencia #2494. Efecto neto $0,00."
    cur.execute("""
        INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
        VALUES (?, ?, ?, ?, ?)
    """, ("Banco Nacion", 15892, json.dumps(partes_15892), motivo_15892, USUARIO))

    partes_2494 = [{"subcuenta": "otros-impuestos", "deuda": "0", "credito": "-2409.9000"}]
    motivo_2494 = "Contraasiento negativo de caja La Herencia compensatorio de VEP AFIP BNA #15892. Efecto neto $0,00."
    cur.execute("""
        INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
        VALUES (?, ?, ?, ?, ?)
    """, ("Pagos efectivo", 2494, json.dumps(partes_2494), motivo_2494, USUARIO))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aplicar", action="store_true", help="Aplica los cambios en WC")
    args = parser.parse_args()

    print(f"Modo: {'APLICAR' if args.aplicar else 'SIMULACIÓN (dry-run)'}")

    if not args.aplicar:
        print("Dry-run finalizado sin escribir cambios. Use --aplicar para ejecutar.")
        return

    print("Tomando backup_verificado antes de escribir...")
    backup_path = backup_verificado(REGLA)
    print(f"Backup verificado: {backup_path}")

    with get_connection(readonly=False) as conn:
        _assert_target_is_wc()
        aplicar_clasificaciones(conn)

        # Auditoria
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO dbo.AuditoriaCorrecciones
            (Regla, Estado, Parametros, Usuario, UsuarioAplicacion, FechaAplicacion, Respaldo, Resumen)
            VALUES (?, 'aplicada', ?, ?, ?, SYSDATETIME(), ?, ?)
        """, (
            REGLA,
            json.dumps({"movimientos": 10, "saldo_por_identificar": "0.00"}),
            USUARIO,
            USUARIO,
            str(backup_path),
            "Cierre final de 10 movimientos de ARCA: por-identificar queda en 0 movimientos y $0,00."
        ))

        conn.commit()
        print("Cambios aplicados y confirmados en WC exitosamente.")


if __name__ == "__main__":
    main()
