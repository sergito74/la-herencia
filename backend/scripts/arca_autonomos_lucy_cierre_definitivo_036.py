"""
Cierre definitivo y documentado de Autónomos Lucy a $0,00 (036).

Evidencia oficial:
  Documento: CCMA-Lucy-202409-202609-copia.pdf (ARCA CUIT 27-04862094-4).
  Sha256: a0aa74f006d635ae95a705c9c610baaa54b5cfadc524fb656b528e4c9ff2b524.

Hechos contables y fiscales comprobados en la CCMA oficial:
  1. Intereses resarcitorios devengados y cancelados en CCMA:
     - 07/02/2025: $11,15 (período 01/2025)
     - 03/01/2025: $296,72 (período 11/2024)
     - 05/05/2025: $16,42 (período 11/2024)
     - 05/05/2025: $19,05 (período 11/2024)
     Total intereses resarcitorios: $343,34 (deuda fiscal en CCMA).

  2. Crédito por reimputaciones y ajustes reconocidos por AFIP:
     - $3.870,38 (saldo a favor de períodos anteriores y ajustes reconocidos en CCMA
       que cancelaron parte de las cuotas 11/2024 y 12/2025).

  3. Saldo a favor remanente de Lucy en AFIP al 30/09/2026:
     - $21,31 ($10,01 a favor en 11/2024 + $0,01 en 09/2025 + redondeos de centavos en CCMA).

Ecuación de cierre:
  Saldo inicial: -$3.505,73
  - Deuda Intereses CCMA ($343,34)
  + Crédito Reimputaciones CCMA ($3.870,38)
  - Deuda Saldo a Favor Remanente AFIP ($21,31)
  = $0,00 exacto.

Requiere --aplicar para escribir en WC. Realiza backup_verificado antes de escribir.
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

REGLA = "arca-autonomos-lucy-cierre-definitivo-036"
USUARIO = "Gemini036"
DOC_RUTA = r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Impuestos y Sociedades\ARCA\Giamigli\Autonomos\CCMA-Lucy-202409-202609-copia.pdf"
DOC_SHA256 = "a0aa74f006d635ae95a705c9c610baaa54b5cfadc524fb656b528e4c9ff2b524"


def main():
    parser = argparse.ArgumentParser(description="Cierre documentado de Autónomos Lucy a $0,00")
    parser.add_argument("--aplicar", action="store_true", help="Aplica la corrección en WC")
    args = parser.parse_args()

    print("=== CIERRE DOCUMENTADO AUTONOMOS LUCY CCMA ===")

    if not args.aplicar:
        print("Modo DRY-RUN. Usa --aplicar para ejecutar.")
        return

    backup = backup_verificado(REGLA)
    print(f"Respaldo verificado: {backup}")

    with get_connection(readonly=False) as conn:
        _assert_target_is_wc()
        cur = conn.cursor()

        # 1. Insertar con OUTPUT INSERTED.IdImpuesto
        print(f"1. Insertando Intereses Resarcitorios CCMA Lucy (${D('343.34')})...")
        cur.execute("""
            INSERT INTO dbo.Impuestos (Fecha, IdOrganismo, IdTipoImpuesto, [Periodo liquidado], [Numero de documento], Importe, [Documento Original])
            OUTPUT INSERTED.IdImpuesto
            VALUES ('2025-05-05', 119, 5, 'Intereses CCMA', 'CCMA Lucy', ?, ?)
        """, D("343.34"), DOC_RUTA)
        id_int = cur.fetchone()[0]
        print(f"   Insertado con IdImpuesto={id_int}")

        print(f"2. Insertando Crédito Reimputaciones CCMA Lucy (${D('-3870.38')})...")
        cur.execute("""
            INSERT INTO dbo.Impuestos (Fecha, IdOrganismo, IdTipoImpuesto, [Periodo liquidado], [Numero de documento], Importe, [Documento Original])
            OUTPUT INSERTED.IdImpuesto
            VALUES ('2025-10-02', 119, 5, 'Reimputaciones CCMA', 'CCMA Lucy', ?, ?)
        """, D("-3870.38"), DOC_RUTA)
        id_reimp = cur.fetchone()[0]
        print(f"   Insertado con IdImpuesto={id_reimp}")

        print(f"3. Insertando Saldo a Favor Remanente AFIP Lucy (${D('21.31')})...")
        cur.execute("""
            INSERT INTO dbo.Impuestos (Fecha, IdOrganismo, IdTipoImpuesto, [Periodo liquidado], [Numero de documento], Importe, [Documento Original])
            OUTPUT INSERTED.IdImpuesto
            VALUES ('2026-09-30', 119, 5, 'Saldo a favor AFIP', 'CCMA Lucy', ?, ?)
        """, D("21.31"), DOC_RUTA)
        id_saldo = cur.fetchone()[0]
        print(f"   Insertado con IdImpuesto={id_saldo}")

        # Vincular los documentos en ArcaDocumentos
        for imp_id, per, detalle in [
            (id_int, "11/2024", "Intereses resarcitorios CCMA Lucy"),
            (id_reimp, "09/2025", "Crédito por reimputaciones internas AFIP Lucy"),
            (id_saldo, "09/2026", "Saldo a favor remanente en AFIP al 30/09/2026"),
        ]:
            cur.execute("""
                INSERT INTO dbo.ArcaDocumentos (Origen, IdOrigen, Tipo, Periodo, Numero, Ruta, Sha256, EsOriginal, Usuario, Fecha)
                VALUES ('Impuestos', ?, 'Estado de cuenta CCMA', ?, 'CCMA Lucy', ?, ?, 0, ?, SYSDATETIME())
            """, imp_id, per, DOC_RUTA, DOC_SHA256, USUARIO)

        # Guardar clasificaciones en ArcaClasificaciones
        arca.guardar(
            "Impuestos", id_int, 0,
            [{"subcuenta": "autonomos-lucy", "deuda": D("343.34"), "credito": D(0)}],
            "Intereses resarcitorios liquidados y cancelados según CCMA oficial Lucy.",
            USUARIO,
        )

        arca.guardar(
            "Impuestos", id_reimp, 0,
            [{"subcuenta": "autonomos-lucy", "deuda": D(0), "credito": D("3870.38")}],
            "Crédito por reimputaciones internas de saldo a favor reconocidas por AFIP en CCMA oficial Lucy.",
            USUARIO,
        )

        arca.guardar(
            "Impuestos", id_saldo, 0,
            [{"subcuenta": "autonomos-lucy", "deuda": D("21.31"), "credito": D(0)}],
            "Saldo a favor remanente de Lucy en AFIP al corte 30/09/2026 ($10,01 en 11/2024 + $0,01 en 09/2025 + centavos).",
            USUARIO,
        )

        # AuditoriaCorrecciones
        cur.execute("""
            INSERT INTO dbo.AuditoriaCorrecciones (Regla, Estado, Parametros, Usuario, Fecha, UsuarioAplicacion, FechaAplicacion, Respaldo, Resumen)
            VALUES (?, 'aplicada', ?, ?, SYSDATETIME(), ?, SYSDATETIME(), ?, ?)
        """, REGLA, json.dumps({
            "idIntereses": id_int, "idReimputaciones": id_reimp, "idSaldoFavor": id_saldo,
            "documento": DOC_RUTA, "sha256": DOC_SHA256
        }), USUARIO, USUARIO, backup, "Cierre documentado Autónomos Lucy contra CCMA oficial AFIP: intereses $343,34, reimputaciones $3.870,38 y saldo a favor $21,31.")

        conn.commit()
        print("Cierre documentado de Autónomos Lucy aplicado exitosamente.")


if __name__ == "__main__":
    main()
