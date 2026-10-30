"""036, 30/10/2026: control de cuentas cerradas. Compara el saldo actual al corte de cada ficha cerrada con el saldo con
que se cerró (en su moneda). Una diferencia significa que algo tocó la cuenta después del cierre (como el subsidio que
Gemini metió en Cargill el 26/10). Solo lectura. Uso (desde backend/): python -m scripts.control_fichas_cerradas_036 [salida.txt]
"""
import sys

from scripts.inventario_cuentas_externas_036 import saldo_a
from src.db.connection import fetch_all

if __name__ == "__main__":
    nombres = {r["i"]: r["n"] for r in fetch_all("SELECT IdContacto i,[Razon Social] n FROM dbo.Contactos", ())}
    fichas = fetch_all("SELECT IdContacto c,SaldoAlCierre s,Moneda m,Corte k,FechaCierre fc FROM dbo.RevisionFichas "
                       "WHERE Estado LIKE 'cerrada%' AND SaldoAlCierre IS NOT NULL", ())
    dif = []
    for f in fichas:
        p, u = saldo_a(f["c"], str(f["k"])[:10] if f["k"] else "2026-09-30")
        hoy = u if f["m"] == "Dolares" else p
        d = round(hoy - float(f["s"]), 2)
        if abs(d) >= 0.02:
            dif.append((abs(d), f["c"], nombres.get(f["c"]), f["m"], str(f["k"])[:10], float(f["s"]), round(hoy, 2), d, str(f["fc"])[:10]))
    lineas = [f"{len(fichas)} fichas cerradas; {len(dif)} cambiaron desde su cierre"]
    lineas += [f"{x[1]:5} {str(x[2])[:30]:30} {x[3][:3]} corte {x[4]} cierre {x[5]:>16,.2f} hoy {x[6]:>16,.2f} dif {x[7]:>14,.2f} cerrada {x[8]}"
               for x in sorted(dif, reverse=True)]
    texto = "\n".join(lineas)
    print(texto)
    if len(sys.argv) > 1:
        open(sys.argv[1], "w", encoding="utf-8").write(texto)
