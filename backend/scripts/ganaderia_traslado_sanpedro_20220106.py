"""052: traslado San Pedro -> La Herencia del 06/01/2022 (DTe 021980187-4, flete Sosa 00001-00000161)."""
import sys
from datetime import date
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from src.db.connection import fetch_all
from src.features.ganaderia import stock
from scripts.ganaderia_tablas_20261125 import _backup

MOTIVO = "DTe SENASA 021980187-4 (invernada); flete Adrián Sosa FC 00001-00000161"
if fetch_all("SELECT 1 x FROM dbo.GanMovimiento WHERE Tipo='Traslado' AND Fecha='2022-01-06'"):
    sys.exit("ya cargado")
print("backup:", _backup())
for cat, cab in ((1, 22), (2, 18)):  # terneras, terneros
    print(cat, cab, stock.registrar_movimiento({"fecha": date(2022, 1, 6).isoformat(), "tipo": "Traslado", "categoria": cat,
          "cabezas": cab, "establecimiento": 2, "establecimientoDestino": 1, "motivo": MOTIVO}, "Claude (052)", confirmar=True))
