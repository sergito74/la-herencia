"""Motor financiero puro. Una coincidencia no es una aplicación contable."""
from collections import Counter
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json

ZERO = Decimal('0.00')
TOL = Decimal('0.10')

def money(v):
    return Decimal(str(v or 0)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()

# Decisión del usuario (2026-09-30): una boleta ya cargada del mismo
# organismo, por el mismo importe y con fecha cercana, respalda al pago
# aunque no exista un vínculo explícito — es lo habitual en el histórico
# (se cargaron boleta y pago por separado, sin conciliarlos). Cada boleta
# respalda a un solo pago: con cuotas fijas mensuales (Municipalidad,
# UATRE) varios pagos tienen el mismo importe, y sin asignación uno a uno
# una sola boleta "cubriría" a todos.
VENTANA_DIAS = 90


def _dias(fecha_pago, fecha_boleta):
    if not fecha_pago or not fecha_boleta:
        return None
    a = date.fromisoformat(str(fecha_pago)[:10])
    b = date.fromisoformat(str(fecha_boleta)[:10])
    return abs((a - b).days)


def _clasificar_base(p):
    """Estados que no dependen de las boletas por coincidencia; None si el pago es elegible."""
    amount = money(p['importe']); respaldo = money(p.get('respaldo'))
    if amount <= 0 or p.get('traspaso'):
        return 'excluido', 'Ingreso, devolución, importe no positivo o traspaso'
    if not p.get('idOrganismo') or not p.get('fecha'):
        return 'pendiente', 'Falta organismo o fecha del pago'
    if p.get('conflicto'):
        return 'pendiente', p['conflicto']
    if respaldo > amount + TOL:
        return 'pendiente', 'Respaldo superior al pago: revisar duplicación'
    if respaldo > 0 and abs(amount - respaldo) <= TOL:
        return 'respaldado', 'Vínculo documental verificable'
    if respaldo > 0:
        return 'pendiente', 'Pago parcialmente respaldado; no generar por el total'
    # Sin fila única y equivalente en la cuenta corriente, generar una
    # boleta agregaría deuda sin el crédito que la compense (ej. pagos de
    # Mercado Libre que no están en la cuenta del organismo).
    if p.get('filasContables') != 1 or abs(money(p.get('creditoContable')) - amount) > TOL:
        return 'pendiente', 'Representación contable ausente, múltiple o distinta del pago'
    return None


def _absorber(pagos, pendientes, absorbentes):
    """Segunda pasada (decisión del usuario 2026-09-30): lo que no coincide
    importe a importe — boletas pagadas en partes o varias pagadas juntas,
    compras al organismo, reintegros — cubre a los pagos de fecha más
    cercana hasta agotar su importe. Verificado contra `WC`: con esto el
    total a generar de cada organismo es exactamente su saldo a favor.
    Devuelve el importe cubierto de cada pago."""
    cubierto = {i: ZERO for i in pendientes}
    for doc in sorted(absorbentes, key=lambda d: (str(d.get('fecha') or ''), str(d.get('id')))):
        resto = money(doc['importe'])
        while resto > TOL:
            candidatos = [i for i in pendientes if money(pagos[i]['importe']) - cubierto[i] > TOL]
            if not candidatos:
                return cubierto
            i = min(candidatos, key=lambda i: (_dias(pagos[i].get('fecha'), doc.get('fecha')) or 10**6, pagos[i]['fecha'], i))
            toma = min(resto, money(pagos[i]['importe']) - cubierto[i])
            cubierto[i] += toma
            resto -= toma
    return cubierto


def diagnosticar(pagos, boletas, saldo, otros_documentos=False, documentos_extra=(), generacion_habilitada=True,
                 motivo_bloqueo=None):
    abiertos = [b for b in boletas if money(b['saldo']) > TOL]
    base = [_clasificar_base(p) for p in pagos]

    # Percepciones sin boleta por naturaleza (ej. "RECAUDACION ARBA"): no se
    # emparejan ni se absorben — se registran desde el pago, por el total.
    propios = {i for i, p in enumerate(pagos) if base[i] is None and p.get('sinBoletaPorNaturaleza')}

    pares = []
    for i, p in enumerate(pagos):
        if base[i] is not None or i in propios:
            continue
        for b in abiertos:
            dias = _dias(p.get('fecha'), b.get('fecha'))
            if dias is not None and dias <= VENTANA_DIAS and abs(money(b['saldo']) - money(p['importe'])) <= TOL:
                pares.append((dias, i, b['idImpuesto']))
    asignada = {}
    usadas = set()
    for dias, i, id_impuesto in sorted(pares, key=lambda x: (x[0], x[1], x[2])):
        if i in asignada or id_impuesto in usadas:
            continue
        asignada[i] = id_impuesto
        usadas.add(id_impuesto)

    pendientes = [i for i in range(len(pagos)) if base[i] is None and i not in asignada and i not in propios]
    absorbentes = [dict(id=f"impuesto:{b['idImpuesto']}", fecha=b.get('fecha'), importe=b['saldo'])
                   for b in abiertos if b['idImpuesto'] not in usadas]
    absorbentes += list(documentos_extra)
    # Un reintegro del organismo (pago con importe negativo) compensa lo pagado.
    absorbentes += [dict(id=f"reintegro:{p['medio']}:{p['idMovimiento']}", fecha=p.get('fecha'), importe=-money(p['importe']))
                    for p in pagos if money(p['importe']) < -TOL and not p.get('traspaso')]
    cubierto = _absorber(pagos, pendientes, absorbentes)

    rows = []
    for i, p in enumerate(pagos):
        row = dict(p)
        amount = money(p['importe'])
        a_generar = ZERO
        if base[i] is not None:
            state, reason = base[i]
        elif i in propios:
            if generacion_habilitada:
                state, reason, a_generar = 'faltante', 'Percepción de Ingresos Brutos (recaudación bancaria): sin boleta, se registra desde el pago', amount
            else:
                state, reason = 'pendiente', motivo_bloqueo or 'Generación deshabilitada para este organismo'
        elif i in asignada:
            state, reason = 'respaldado', 'Boleta del mismo importe y fecha cercana (sin vínculo explícito)'
        elif amount - cubierto[i] <= TOL:
            state, reason = 'respaldado', 'Cubierto por boletas u otros documentos sin coincidencia exacta de importe'
        elif not generacion_habilitada:
            state, reason = 'pendiente', motivo_bloqueo or 'Generación deshabilitada para este organismo'
        else:
            a_generar = amount - cubierto.get(i, ZERO)
            state = 'faltante'
            reason = ('Pago sin boleta del mismo importe dentro de los 90 días' if a_generar == amount
                      else 'Pago cubierto en parte por otros documentos: se genera solo lo descubierto')
        row.update(estado=state, motivo=reason, importe=amount, respaldo=money(p.get('respaldo')),
                   boletaPorCoincidencia=asignada.get(i), importeCubierto=cubierto.get(i, ZERO),
                   importeAGenerar=a_generar)
        row['huella'] = digest(row)
        rows.append(row)
    return rows

def resumen(rows,saldo):
    counts=Counter(p['estado'] for p in rows)
    totals={s:sum((p['importe'] for p in rows if p['estado']==s),ZERO) for s in counts}
    faltante=sum((p['importeAGenerar'] for p in rows if p['estado']=='faltante'),ZERO)
    return dict(total=len(rows),totalesPorEstado={s:dict(cantidad=counts[s],importe=totals[s]) for s in counts},
                saldoActual=money(saldo),totalFaltanteConfirmado=faltante,
                saldoProyectado=money(saldo)+faltante,diferenciaNoExplicada=money(saldo)+faltante,
                respaldados=counts['respaldado'],pendientes=len(rows)-counts['respaldado'])
