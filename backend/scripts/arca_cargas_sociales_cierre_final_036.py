import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path("backend").resolve()))
from src.features.cajas_efectivo.operaciones import read
from src.db.connection import get_connection

# 1. Registrar PE 2379 ($5.75) como autonomos-lucy (cancela Impuesto #930 de Autónomos Lucy Intereses 10 2022)
# 2. Insertar obligación omitida F931 09 2024 de $7.344,68 (cancela Pago por socio 2663)

with get_connection(readonly=False) as conn:
    cur = conn.cursor()
    
    # 1. Clasificar PE 2379 en autonomos-lucy
    rep_2379 = json.dumps([{'subcuenta': 'autonomos-lucy', 'deuda': 0, 'credito': 5.75}])
    cur.execute("""
        INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
        VALUES ('Pagos efectivo', 2379, ?, 'Intereses Autonomos 10/2022 coincidente con Impuestos[930]', 'Gemini036')
    """, (rep_2379,))
    print("1. PE 2379 ($5.75) clasificado en autonomos-lucy.")
    
    # 2. Insertar F931 09 2024 chico ($7.344,68)
    cur.execute("""
        INSERT INTO dbo.Impuestos (Fecha, IdOrganismo, IdTipoImpuesto, [Periodo liquidado], [Numero de documento], Importe, [Documento Original])
        OUTPUT INSERTED.IdImpuesto
        VALUES ('2024-10-10', 119, 2, '09 2024', 'Servicio Domestico', 7344.68, NULL)
    """)
    id_f931_nuevo = cur.fetchone()[0]
    
    rep_f931_nuevo = json.dumps([{'subcuenta': 'cargas-sociales', 'deuda': 7344.68, 'credito': 0}])
    cur.execute("""
        INSERT INTO dbo.ArcaClasificaciones (Origen, IdOrigen, Reparto, Motivo, Usuario)
        VALUES ('Impuestos', ?, ?, 'Obligacion Cargas Sociales 09 2024 cancelada por Pago por socio 2663', 'Gemini036')
    """, (id_f931_nuevo, rep_f931_nuevo))
    print(f"2. F931 09/2024 chico insertado (IdImpuesto={id_f931_nuevo}, $7.344,68).")
    
    conn.commit()

print("Ajustes aplicados correctamente.")
