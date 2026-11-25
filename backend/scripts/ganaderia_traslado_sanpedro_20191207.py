"""052: traslado La Herencia -> San Pedro del 07/12/2019 (DTe 017616263-5 y 017616267-8, fletes Gimenez FC 1174)."""
import sys
from datetime import date
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from src.db.connection import fetch_all
from src.features.ganaderia import stock
from scripts.ganaderia_tablas_20261125 import _backup

MOTIVO = "DTe SENASA 017616263-5 y 017616267-8 del 06/12/2019; fletes Transporte Gimenez FC 1174"
if fetch_all("SELECT 1 x FROM dbo.GanMovimiento WHERE Tipo='Traslado' AND Fecha='2019-12-07'"):
    sys.exit("ya cargado")
cats = {r["n"].lower(): r["i"] for r in fetch_all("SELECT IdCategoria i, Nombre n FROM dbo.GanCategoria")}
print(cats)
print("backup:", _backup())
for nombre, cab in (("vacas", 65), ("toros", 4)):
    i = stock.registrar_movimiento({"fecha": date(2019, 12, 7).isoformat(), "tipo": "Traslado", "categoria": cats[nombre],
                                    "cabezas": cab, "establecimiento": 1, "establecimientoDestino": 2,
                                    "motivo": MOTIVO}, "Claude (052)", confirmar=True)
    print(nombre, cab, "-> movimiento", i)
