"""Precisión del coeficiente IVA solo en renglones financieros.

IVA es SQL real: 1+IVA/100 se evalúa con precisión simple y desvía centavos
en ajustes grandes. Convertir IVA a float antes de dividir exclusivamente en
ND de diferencia de cambio en pesos con renglones financieros. El resto
mantiene explícitamente el coeficiente anterior.
Se aplica dentro de transacción con respaldo y auditoría del script llamador.
"""
import re

from src.db.connection import fetch_all, _reconciliation_connection

VIEWS = ("dbo.vw_Compras_ImporteDocumento", "dbo.vw_Cns_Total_Det_Compras")
MARKER = "/* precision IVA financiero 036 */"


def build(name, definition):
    if MARKER in definition:
        return definition
    if name == VIEWS[0]:
        old = "(1 + ISNULL(dc.IVA, 0) / 100.0)"
        iva, flag = "ISNULL(dc.IVA, 0)", "dc.[Ajuste financiero]"
        header = "cfx"
    else:
        old = "(1 + (d.IVA / 100.0))"
        iva, flag = "d.IVA", "d.[Ajuste financiero]"
        header = "c"
    assert definition.count(old) == 1, f"Definicion inesperada:{name}"
    new = ("(" + MARKER + f" CASE WHEN ISNULL({flag},0)=1 "
           f"AND ISNULL({header}.[Ajusta Tipo Cambio],0)=1 AND {header}.Moneda='Pesos' "
           f"AND {header}.[Tipo documento] COLLATE Latin1_General_CI_AI='Nota de Debito' "
           f"THEN 1.0+CONVERT(float,{iva})/100.0 "
           f"ELSE CONVERT(float,{old}) END)")
    result = definition.replace(old, new)
    if name == VIEWS[0]:
        source = "FROM dbo.Det_Compras dc"
        assert result.count(source) == 1
        result = result.replace(source, source + " LEFT JOIN dbo.Compras cfx ON cfx.IdDeuda=dc.IdCompra")
    return re.sub(r"^\s*CREATE\s+(?:OR\s+ALTER\s+)?VIEW", "ALTER VIEW", result, count=1, flags=re.IGNORECASE)


def prepare():
    out = []
    for name in VIEWS:
        old = fetch_all("SELECT OBJECT_DEFINITION(OBJECT_ID(?)) AS d", (name,))[0]["d"]
        out.append({"nombre": name, "antes": old, "despues": build(name, old)})
    return out


def previous_totals():
    return fetch_all("SELECT c.IdDeuda,v.ImporteDocumento,t.GranTotal FROM dbo.Compras c "
                     "JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda=c.IdDeuda "
                     "JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda=c.IdDeuda "
                     "WHERE EXISTS(SELECT 1 FROM dbo.Det_Compras d WHERE d.IdCompra=c.IdDeuda AND d.[Ajuste financiero]=1) ORDER BY c.IdDeuda", ())


def apply(changes):
    conn = _reconciliation_connection.get()
    assert conn is not None, "Se requiere transaccion exterior respaldada"
    before = previous_totals()
    cur = conn.cursor()
    assert cur.execute("SELECT DB_NAME()").fetchone()[0] == "WC"
    for change in changes:
        assert cur.execute("SELECT OBJECT_DEFINITION(OBJECT_ID(?))", (change["nombre"],)).fetchone()[0] == change["antes"]
        if change["antes"] != change["despues"]:
            cur.execute(change["despues"])
    after = previous_totals()
    assert len(before) == len(after)
    for old, new in zip(before, after):
        assert old["IdDeuda"] == new["IdDeuda"]
        for k in ("ImporteDocumento", "GranTotal"):
            assert round(old[k], 2) == round(new[k], 2), f"Cambio visible previo:{old['IdDeuda']} {k}"
    return {"antes": before, "despues": after}
