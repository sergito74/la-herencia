"""052: eventos de stock de La Herencia 2016-2026 (nacimientos, cambios de categoría, compras, muertes probables y
diferencias de recuento) reconstruidos desde las actas de vacunación (planilla = actas), las ventas cargadas y los DTe
de SENASA (histórico de stock de SIGSA). Aprobado por Sergio 26/11/2026. Corre una sola vez (aborta si ya cargó).

Regla, por intervalo entre recuentos:
- Compras de hacienda (SENASA "movimiento entrante"): Yanquelen 35 vacas preñadas, Casamu 1 toro, Madelan 7 vaq.
  preñadas + 28 vaquillonas.
- Cambios de categoría solo por lo que el recuento siguiente necesita: novillito→novillo, torito→toro,
  vaquillona→vaca, ternera→vaquillona, ternero→torito/toro, ternero→novillito (un día antes del acta).
- Nacimientos = terneros del acta que no estaban (1/8 si el acta es de primavera; si no, 45 días antes).
- Lo que no cierra: torito→toro si faltan toritos y sobran toros; faltantes = muerte probable; sobrantes = ajuste.
"""
import sys
from collections import defaultdict
from datetime import date, timedelta

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from src.db.connection import fetch_all  # noqa: E402
from src.features.ganaderia import stock  # noqa: E402
from scripts.ganaderia_tablas_20261125 import _backup  # noqa: E402

LH = 1
FIRMA = "Claude (052) LH"
PADRE = {10: 11, 12: 11, 13: 11, 6: 5, 7: 5, 3: 1}
COMPRAS = [(date(2018, 2, 8), 12, 35, "Compra Yanquelen 0003-00000005: 35 vacas preñadas (DTe entrante 12/02/2018)"),
           (date(2018, 9, 4), 14, 1, "Compra Casamu 0003-00000256: toro pedigree (DTe entrante 01/09/2018)"),
           (date(2021, 3, 31), 7, 7, "Compra Madelan 00011-00017347: 7 vaquillonas preñadas (DTe 31/03/2021)"),
           (date(2021, 3, 31), 5, 28, "Compra Madelan 00011-00017348: 28 vaquillonas (DTe 31/03/2021)")]
CAMBIOS = [(4, 8), (9, 14), (14, 9), (5, 11), (1, 5), (2, 9), (2, 14), (2, 4)]  # (14, 9): el acta reclasifica toros como toritos


def mov(fecha, tipo, cat, cab, motivo, destino=None):
    d = {"fecha": fecha.isoformat(), "tipo": tipo, "categoria": cat, "cabezas": cab, "establecimiento": LH,
         "motivo": motivo[:300], "causa": "Sin determinar" if tipo == "Muerte" else None}
    if destino:
        d["categoriaDestino"] = destino
    return stock.registrar_movimiento(d, FIRMA, confirmar=True)


def recuentos():
    out = []
    for r in fetch_all("SELECT IdRecuento i, Fecha f FROM dbo.GanRecuento WHERE IdEstablecimiento=1 ORDER BY Fecha"):
        det = defaultdict(int)
        for d in fetch_all("SELECT IdCategoria c, Cabezas n FROM dbo.GanRecuentoDetalle WHERE IdRecuento=? "
                           "AND IdContactoDueno IS NULL", (r["i"],)):
            det[PADRE.get(d["c"], d["c"])] += d["n"]
        out.append((date.fromisoformat(str(r["f"])[:10]), det))
    return out


def main():
    if fetch_all("SELECT TOP 1 1 x FROM dbo.GanMovimiento WHERE CreadoPor = ?", (FIRMA,)):
        sys.exit("ya cargado")
    print("backup:", _backup())
    for f, c, n, t in COMPRAS:
        mov(f, "Compra", c, n, t)
    movs = fetch_all("SELECT Fecha f, Tipo t, IdCategoria c, Cabezas n, IdEstablecimiento e FROM dbo.GanMovimiento "
                     "WHERE Anulado=0 AND IdContactoDueno IS NULL AND Tipo IN ('Venta','Traslado','Compra') "
                     "AND (IdEstablecimiento=1 OR (Tipo='Traslado' AND IdEstablecimientoDestino=1))")
    rec = recuentos()
    for (fa, A), (fb, B) in zip(rec, rec[1:]):
        st = defaultdict(int, {c: n for c, n in A.items()})
        primera_venta = {}
        for m in movs:
            f = date.fromisoformat(str(m["f"])[:10])
            if fa < f <= fb:
                c = PADRE.get(m["c"], m["c"])
                entra = m["t"] == "Compra" or (m["t"] == "Traslado" and m["e"] != LH)
                if not entra:
                    primera_venta[c] = min(primera_venta.get(c, f), f)
                st[c] += m["n"] if entra else -m["n"]
                for o in {8: (4, 2), 4: (2,), 9: (2,)}.get(c, ()):
                    if st[c] < 0 and st[o] > 0:
                        k = min(-st[c], st[o]); st[c] += k; st[o] -= k
        nota = f"entre actas {fa:%d/%m/%Y} y {fb:%d/%m/%Y}"
        dia = fb - timedelta(days=1)
        for o, d in CAMBIOS:
            n = min(max(st[o], 0), max(B.get(d, 0) - st[d], 0))
            if n:
                st[o] -= n; st[d] += n
                # el pase ocurre antes de la primera venta de la categoría nueva (novedad SENASA 10/10/2025)
                cuando = min(dia, primera_venta.get(d, dia) - timedelta(days=1))
                mov(max(cuando, fa + timedelta(days=1)), "CambioCategoria", o, n,
                    f"Cambio de categoría {nota} (regla por actas)", destino=d)
        fn = date(fb.year, 8, 1) if fb.month >= 9 else fb - timedelta(days=45)
        for c in (1, 2):
            if B.get(c, 0) > st[c]:
                mov(fn, "Nacimiento", c, B[c] - st[c], f"Nacimientos {nota}; fecha estimada")
                st[c] = B[c]
    # 5 toros vendidos con liquidación del 22/11/2017 contados en el acta del 25/11/2017 (DTe de salida 15/12/2017)
    mov(date(2018, 4, 1), "AjusteRecuento", 14, -5, "5 toros vendidos (liquidaciones del 22/11/2017) contados en el acta "
        "del 25/11/2017: salieron con DTe del 15/12/2017, posterior al acta (Sergio 26/11/2026).")
    # lo que no cierra, recuento por recuento, con el motor real
    for fb, _ in rec[1:]:
        dif = {d["categoria"]: d["diferencia"] for d in stock.stock(fb + timedelta(days=1), LH, "propia")["sinExplicar"]}
        ids = {r["n"]: r["i"] for r in fetch_all("SELECT IdCategoria i, Nombre n FROM dbo.GanCategoria")}
        dia, nota = fb - timedelta(days=1), f"faltante/sobrante al acta {fb:%d/%m/%Y}"
        # dentro de una familia (vacas/preñadas/conserva, vaquillonas, terneras, toritos→toros) es cambio de categoría
        fam = {ids[n]: PADRE.get(ids[n], ids[n]) for n in dif}
        fam.update({ids["Toritos"]: 14, ids["Toros"]: 14} if "Toritos" in dif or "Toros" in dif else {})
        for neg in [n for n in dif if dif[n] < 0]:
            for pos in [n for n in dif if dif[n] > 0]:
                if dif[neg] < 0 and fam.get(ids[neg]) == fam.get(ids[pos]):
                    n = min(-dif[neg], dif[pos])
                    mov(dia, "CambioCategoria", ids[neg], n, f"Cambio de categoría, {nota}", destino=ids[pos])
                    dif[neg] += n; dif[pos] -= n
        for nom, d in dif.items():
            if d < 0:
                mov(dia, "Muerte", ids[nom], -d, f"Muerte probable, {nota}; fecha estimada (Sergio 26/11/2026)")
            elif d > 0:
                mov(dia, "AjusteRecuento", ids[nom], d, f"Sobrante sin explicar, {nota} (Sergio 26/11/2026)")
    for fb, _ in rec[1:]:
        print(fb, stock.stock(fb + timedelta(days=1), LH, "propia")["sinExplicar"])


if __name__ == "__main__":
    main()
