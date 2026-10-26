"""
Incorporación de 4 Certificados de Retención de IVA Granos Cargill (036).

Certificados emitidos por Cargill S.A.C.I. en mayo y junio de 2020:
  1. IdLiquidacion=116, Nro Certificado='1079-00019236', Importe=$25.929,57, Fecha=2020-05-26
     Ruta: C:\\Users\\Sergio\\Dropbox\\Giamigli de Bolivar SA\\Ventas\\Retenciones 04 2020 - 03 2021\\30712114602_653_CE_00020876_RET_1.pdf
  2. IdLiquidacion=117, Nro Certificado='1079-00019293', Importe=$2.222,53, Fecha=2020-05-28
     Ruta: C:\\Users\\Sergio\\Dropbox\\Giamigli de Bolivar SA\\Ventas\\Retenciones 04 2020 - 03 2021\\30712114602_653_CE_00020935_RET_1.pdf
  3. IdLiquidacion=118, Nro Certificado='1079-00019294', Importe=$81.313,19, Fecha=2020-05-28
     Ruta: C:\\Users\\Sergio\\Dropbox\\Giamigli de Bolivar SA\\Ventas\\Retenciones 04 2020 - 03 2021\\30712114602_653_CE_00020935_RET_2.pdf
  4. IdLiquidacion=119, Nro Certificado='1079-00019435', Importe=$323,32, Fecha=2020-06-05
     Ruta: C:\\Users\\Sergio\\Dropbox\\Giamigli de Bolivar SA\\Ventas\\Retenciones 04 2020 - 03 2021\\30712114602_653_CE_00021087_RET_1.pdf

Total incorporado: $109.788,61.
Esto cierra la subcuenta 'iva' emparejando los reintegros bancarios de AFIP SNP.

Requiere --aplicar para escribir en WC. Realiza backup_verificado antes de escribir.
"""
import argparse
import sys
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db.connection import get_connection, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado

CERTS = [
    {
        "idLiquidacion": 116,
        "nroCertificado": "1079-00019236",
        "agente": 258,
        "importe": D("25929.57"),
        "imagen": r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Ventas\Retenciones 04 2020 - 03 2021\30712114602_653_CE_00020876_RET_1.pdf"
    },
    {
        "idLiquidacion": 117,
        "nroCertificado": "1079-00019293",
        "agente": 258,
        "importe": D("2222.53"),
        "imagen": r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Ventas\Retenciones 04 2020 - 03 2021\30712114602_653_CE_00020935_RET_1.pdf"
    },
    {
        "idLiquidacion": 118,
        "nroCertificado": "1079-00019294",
        "agente": 258,
        "importe": D("81313.19"),
        "imagen": r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Ventas\Retenciones 04 2020 - 03 2021\30712114602_653_CE_00020935_RET_2.pdf"
    },
    {
        "idLiquidacion": 119,
        "nroCertificado": "1079-00019435",
        "agente": 258,
        "importe": D("323.32"),
        "imagen": r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Ventas\Retenciones 04 2020 - 03 2021\30712114602_653_CE_00021087_RET_1.pdf"
    },
]


def main():
    parser = argparse.ArgumentParser(description="Incorpora 4 certificados Cargill en dbo.[Retenciones IVA Granos]")
    parser.add_argument("--aplicar", action="store_true", help="Aplica la inserción en WC")
    args = parser.parse_args()

    print("=== INCORPORACION 4 CERTIFICADOS CARGILL 2020 ===")
    total = sum(c["importe"] for c in CERTS)
    print(f"Total certificados a insertar: ${total:,.2f}")

    if not args.aplicar:
        print("Modo DRY-RUN. Usa --aplicar para ejecutar.")
        return

    backup = backup_verificado("retenciones_iva_cargill_4certs_036")
    print(f"Respaldo verificado: {backup}")

    with get_connection(readonly=False) as conn:
        _assert_target_is_wc()
        cur = conn.cursor()

        for c in CERTS:
            cur.execute("SELECT 1 FROM dbo.[Retenciones IVA Granos] WHERE IdLiquidacion = ?", c["idLiquidacion"])
            if cur.fetchone():
                print(f"Certificado para IdLiquidacion={c['idLiquidacion']} ya existe, omitiendo.")
                continue

            # Obtener siguiente IdRetencion
            cur.execute("SELECT ISNULL(MAX(IdRetencion), 0) + 1 FROM dbo.[Retenciones IVA Granos]")
            next_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO dbo.[Retenciones IVA Granos]
                (IdRetencion, IdLiquidacion, [Nro Certificado], [Agente Retencion], [Importe Retenido], [Importe Devolucion], Imagen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, next_id, c["idLiquidacion"], c["nroCertificado"], c["agente"], c["importe"], c["importe"], c["imagen"])
            print(f"Insertado IdRetencion={next_id}, IdLiquidacion={c['idLiquidacion']}, Nro={c['nroCertificado']}, Importe=${c['importe']:,.2f}")

        conn.commit()
        print("Inserción completada y confirmada exitosamente.")


if __name__ == "__main__":
    main()
