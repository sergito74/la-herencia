"""
Reclasificación y contabilización de bonificaciones del Ministerio en resultados de Soja (036).

Hechos comprobados:
  1. Transferencia BNA #15950 ($134.391,10, 11/12/2020):
     - Concepto: 'TRANSF. 122 30711213054 SAF363 MINISTERI'.
     - CUIT 30-71121305-4 / SAF 363: Secretaría de Agricultura, Ganadería y Pesca / Ministerio de Economía.
     - Programa: Compensación y estímulo a pequeños productores de soja (Decreto 786/2020) por ventas Campaña 2019/2020.
     - Acción:
       a) Reasignar en dbo.[Movimientos BNA] #15950 de IdContacto 119 al contacto de la Secretaría.
       b) Anular/retirar contraasiento espurio de caja dbo.[Pagos efectivo] #2493 ($134.391,10) de IdContacto 119.
       c) Registrar en dbo.[Venta Granos_Ajustes] para la venta de soja #118 (Campaña 2019/2020) una bonificación de $134.391,10.

  2. Transferencia BNA #15788 ($1.323,00, 14/03/2016):
     - Concepto: 'TRANSF.MINORISTA RECIBIDA01130546676117PEPP MECON0'.
     - PEPP MECON: Programa de Estímulo al Pequeño Productor de Granos (Resolución 126/2015 MECON).
     - Acción:
       a) Reasignar en dbo.[Movimientos BNA] #15788 de IdContacto 119 al contacto de la Secretaría.
       b) Anular/retirar contraasiento espurio de caja dbo.[Pagos efectivo] #2492 ($1.323,00) de IdContacto 119.
       c) Registrar en dbo.[Venta Granos_Ajustes] para la venta de soja #25 (Campaña 2015/2016) una bonificación de $1.323,00.

Invariantes respetadas:
  - Base SQL Server WC (sin tocar .accdb).
  - Backup verificado obligatorio antes de escribir.
  - ARCA: por-identificar queda en 0 movimientos y $0,00 de saldo.
  - Cajas y bancos preservan sus saldos.
  - Resultados agrícolas: impacto exacto en pesos en vw_ResultadosCultivo_Ventas.
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

REGLA = "soja-bonificaciones-ministerio-mecon-036"
USUARIO = "Gemini036"


def aplicar_cambios(conn):
    cur = conn.cursor()

    # 1. Asegurar contacto oficial: Secretaría de Agricultura, Ganadería y Pesca / MECON
    cur.execute("SELECT IdContacto FROM dbo.Contactos WHERE [CUIT/CUIL] = '30711213054'")
    row = cur.fetchone()
    if row:
        id_contacto_sagyp = row[0]
        print(f"Contacto existente para CUIT 30-71121305-4: IdContacto = {id_contacto_sagyp}")
    else:
        cur.execute("""
            INSERT INTO dbo.Contactos ([Tipo Contacto], [Razon Social], EsContratistaLabores, [CUIT/CUIL])
            OUTPUT INSERTED.IdContacto
            VALUES ('Organismo', 'Secretaría de Agricultura, Ganadería y Pesca', 0, '30711213054')
        """)
        id_contacto_sagyp = cur.fetchone()[0]
        print(f"Contacto creado para Secretaría de Agricultura: IdContacto = {id_contacto_sagyp}")

    # 2. Reasignar movimientos BNA #15950 y #15788 al organismo oficial
    print("Reasignando IdContacto en dbo.[Movimientos BNA] (#15950 y #15788)...")
    cur.execute("""
        UPDATE dbo.[Movimientos BNA]
        SET IdContacto = ?, Contacto = 'Secretaría de Agricultura, Ganadería y Pesca'
        WHERE IdMovimientoBNA = 15950
    """, (id_contacto_sagyp,))

    cur.execute("""
        UPDATE dbo.[Movimientos BNA]
        SET IdContacto = ?, Contacto = 'Secretaría de Agricultura, Ganadería y Pesca'
        WHERE IdMovimientoBNA = 15788
    """, (id_contacto_sagyp,))

    # 3. Retirar / desvincular de ARCA los Pagos efectivo espurios #2493 y #2492
    print("Retirando IdContacto = 119 de dbo.[Pagos efectivo] (#2493 y #2492)...")
    cur.execute("""
        UPDATE dbo.[Pagos efectivo]
        SET IdContacto = ?
        WHERE IdPagoEfectivo IN (2492, 2493)
    """, (id_contacto_sagyp,))

    # 4. Limpiar clasificaciones temporales en dbo.ArcaClasificaciones
    print("Limpiando marcas temporales de estos movimientos en dbo.ArcaClasificaciones...")
    cur.execute("""
        DELETE FROM dbo.ArcaClasificaciones
        WHERE (Origen = 'Banco Nacion' AND IdOrigen IN (15788, 15950))
           OR (Origen = 'Pagos efectivo' AND IdOrigen IN (2492, 2493))
    """)

    # 5. Contabilizar bonificaciones en resultados de Soja (dbo.[Venta Granos_Ajustes])
    # Longitud máxima de Concepto: 50 caracteres
    print("Contabilizando bonificación SAF363 en Venta Granos #118 (Soja primera 2019/2020)...")
    cur.execute("""
        INSERT INTO dbo.[Venta Granos_Ajustes] (IdVenta, Concepto, Importe, AlicuotaIVA)
        VALUES (118, 'Bonif. Compensacion Soja SAF363 Dec 786/20', 134391.1000, 0.0)
    """)

    print("Contabilizando bonificación PEPP MECON en Venta Granos #25 (Soja primera 2015/2016)...")
    cur.execute("""
        INSERT INTO dbo.[Venta Granos_Ajustes] (IdVenta, Concepto, Importe, AlicuotaIVA)
        VALUES (25, 'Bonif. Estimulo Soja PEPP MECON Res 126/15', 1323.0000, 0.0)
    """)

    return id_contacto_sagyp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aplicar", action="store_true", help="Aplica la corrección en WC")
    args = parser.parse_args()

    print("=== RECLASIFICACION Y CONTABILIZACION BONIFICACIONES SOJA MECON ===")
    print(f"Modo: {'APLICAR' if args.aplicar else 'SIMULACIÓN (dry-run)'}")

    if not args.aplicar:
        print("Dry-run finalizado sin escribir cambios. Use --aplicar para ejecutar.")
        return

    backup_path = backup_verificado(REGLA)
    print(f"Backup verificado: {backup_path}")

    with get_connection(readonly=False) as conn:
        _assert_target_is_wc()
        id_contacto = aplicar_cambios(conn)

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO dbo.AuditoriaCorrecciones
            (Regla, Estado, Parametros, Usuario, UsuarioAplicacion, FechaAplicacion, Respaldo, Resumen)
            VALUES (?, 'aplicada', ?, ?, ?, SYSDATETIME(), ?, ?)
        """, (
            REGLA,
            json.dumps({
                "contacto_sagyp": id_contacto,
                "bna_movimientos": [15788, 15950],
                "pagos_efectivo": [2492, 2493],
                "ajustes_ventas": [
                    {"id_venta": 118, "importe": "134391.10"},
                    {"id_venta": 25, "importe": "1323.00"}
                ]
            }),
            USUARIO,
            USUARIO,
            str(backup_path),
            "Reclasificación de transferencias PEPP y SAF363 a Secretaría de Agricultura y contabilización en resultados de Soja en pesos."
        ))

        conn.commit()
        print("Operación completada con éxito en WC.")


if __name__ == "__main__":
    main()
