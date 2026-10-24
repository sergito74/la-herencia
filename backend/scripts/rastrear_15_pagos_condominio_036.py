"""Rastreo acotado SOLO LECTURA; candidatos no equivalen a conciliación.

Ejecutar desde backend. Guarda evidencia local ignorada, sin escribir WC ni fuentes.
Las observaciones de PDF son transcripciones de inspección visual, no OCR automático.
"""

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

from src.features.cajas_efectivo.operaciones import read

IDS = (28, 190, 191, 192, 193, 194, 290, 315, 333, 378, 441, 442, 467, 503, 561)
ROOT = Path("C:/Users/Sergio/Documents")
LSC = ROOT / "Alquileres urbanos/Condominio LSC"
HERENCIA = ROOT / "La Herencia"
OUT = Path(__file__).resolve().parents[2] / "backups/condominio-15-medios-036"
PDFS = {
    28: (
        "Sucesion/2011/20111004_JaureguiyMorales.pdf",
        "Factura a cuenta corriente; no recibo del cheque.",
    ),
    315: (
        "Giamigli/2012/20120913_NaldoLombardi.pdf",
        "Total1578; recibimos Cta.Cte. No identifica tarjeta ni titular.",
    ),
    333: (
        "Giamigli/2012/20121112_ARBA.pdf",
        "Boleta cuota3/2012 por10004.70; no acredita cuenta de origen.",
    ),
    378: (
        "Giamigli/2013/20130312_ARBA.pdf",
        "Boleta cuota1/2013 por10004.70; vence12/03, pago registrado11/03. Sin cuenta de origen.",
    ),
    441: (
        "Giamigli/2013/20130715_YPFNordelta.pdf",
        "Total175.04; recibido EFECTIVO175.03 y otro pago0.01. Contradice medio10.",
    ),
    442: (
        "Giamigli/2013/20130718_EESSSaladillo.pdf",
        "Total204.44; recibido EFECTIVO. Contradice medio10.",
    ),
    467: (
        "Giamigli/2013/20130909_YPFNordelta.pdf",
        "Total140.05; recibido EFECTIVO. Contradice medio10.",
    ),
    503: (
        "Giamigli/2013/20131205_CooperativaAgropecuaria 001.pdf",
        "Total2253.03; recibido TARJETA DE CREDITO; pago2253.04. Titular sin identificar.",
    ),
    561: (
        "Giamigli/2014/20140307_Easy.pdf",
        "Factura1266-00024737 continúa en página2: total1361.54, VISA1362 y vuelto0.46; "
        "pago1250.97. Diferencia110.57.",
    ),
}


def money(value):
    return Decimal(str(value)).quantize(Decimal(".01"))


def day(value):
    return date.fromisoformat(str(value)[:10])


def candidates(rows, payment, days=5):
    return [
        row
        for row in rows
        if abs(money(row["importe"])) == money(payment["importe"])
        and abs((day(row["fecha"]) - day(payment["fecha"])).days) <= days
    ]


def workbook(path, sheet):
    w = load_workbook(path, read_only=True, data_only=True)
    try:
        return list(w[sheet].values)
    finally:
        w.close()


def fingerprint(path):
    return {"ruta": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def run():
    marks = ",".join("?" for _ in IDS)
    payments = read(
        "SELECT p.IdPagoEfectivo id,p.Fecha fecha,p.IdContacto contacto,c.[Razon Social] nombre,"
        "p.IdOperacion operacion,p.[Importe imputado] importe,p.IdFormaPago medio,"
        "p.[Numero documento] numero,p.Caja caja FROM dbo.vw_PagosEfectivoVigentes p "
        "LEFT JOIN dbo.Contactos c ON c.IdContacto=p.IdContacto "
        f"WHERE p.IdPagoEfectivo IN ({marks}) ORDER BY p.Fecha,p.IdPagoEfectivo",
        IDS,
    )
    assert {p["id"] for p in payments} == set(IDS), "Cambió el universo de pagos"
    assert all(p["caja"] == "Condominio" for p in payments)
    assert sum(p["importe"] for p in payments) == Decimal("32042.94")
    banks = read(
        "SELECT IdMovimientoBNA id,[Fecha / Hora Mov#] fecha,Concepto concepto,Importe importe,"
        "IdContacto contacto FROM dbo.[Movimientos BNA] WHERE [Fecha / Hora Mov#]>=? "
        "AND [Fecha / Hora Mov#]<?",
        ("20110101", "20150101"),
    )
    galicia = read(
        "SELECT IdMovimiento id,Fecha fecha,[Débitos] importe,IdContacto contacto "
        "FROM dbo.[Movimientos Galicia] WHERE Fecha>=? AND Fecha<?",
        ("20110101", "20150101"),
    )
    socios = read(
        "SELECT IdMovimiento id,IdSocio socio,Fecha fecha,Importe importe,Tipo tipo,"
        "Origen origen,IdOrigen idOrigen,Motivo motivo,Anulada anulada "
        "FROM dbo.MovimientosCuentaSocio WHERE Fecha>=? AND Fecha<?",
        ("20110101", "20150101"),
    )
    cash = read(
        "SELECT IdMovimiento id,Caja caja,Fecha fecha,Importe importe,IdPagoEfectivo pago,"
        "Concepto concepto,Anulada anulada FROM dbo.MovimientosCajaEfectivo "
        "WHERE Fecha>=? AND Fecha<?",
        ("20110101", "20150101"),
    )
    cards = []
    for table, amount in (
        ("Resumenes Mastercard BNA_Det", "Importe"),
        ("Resumenes Corporativa Nacion_Det", "Importe"),
        ("Resumenes AgroNacion_Det", "Importe Compra"),
    ):
        rows = read(
            f"SELECT [Fecha Compra] fecha,[{amount}] importe,IdContacto contacto "
            f"FROM dbo.[{table}] WHERE [Fecha Compra]>=? AND [Fecha Compra]<?",
            ("20110101", "20150101"),
        )
        cards.extend({**r, "tabla": table} for r in rows)
    values = {
        "recibidos": read(
            "SELECT IdValor,[Numero Valor],Importe,IdEmisor,IdReceptor,Destino "
            "FROM dbo.[Valores Recibidos] WHERE [Numero Valor] IN (?,?)",
            (87678128, 95512293),
        ),
        "propios": read(
            "SELECT IdValor,[Numero cheque],Importe,Comentarios FROM dbo.[Valores propios] "
            "WHERE [Numero cheque] IN (?,?)",
            (87678128, 95512293),
        ),
        "entregados": read(
            "SELECT IdEntrega,Numero,Importe,FechaEntrega,Descripcion FROM dbo.ChequesEntregados "
            "WHERE Numero IN (?,?)",
            ("87678128", "95512293"),
        ),
    }
    source = LSC / "Movimientos LSC.xlsx"
    aportes = HERENCIA / "Administracion y gestion/Aportes de Capital Directores.xlsx"
    source_rows = workbook(source, "Movs")
    aporte_rows = workbook(aportes, "Depositos 1")
    aporte_total = sum(
        (money(r[3]) for r in aporte_rows[1:] if isinstance(r[3], (int, float))), Decimal(0)
    )
    assert aporte_total == Decimal("733781.00")
    extracto = LSC / "Movimientos Condominios.xlsx"
    bank_rows = workbook(extracto, "Extracto Banco")
    source_banks = [
        {"fila": i, "fecha": r[0], "referencia": r[1], "importe": r[6]}
        for i, r in enumerate(bank_rows, 1)
        if isinstance(r[0], datetime) and isinstance(r[6], (int, float)) and r[6] != 0
    ]
    matrix = []
    for p in payments:
        source_matches = [
            {"fila": i, "referencia": r[2], "numero": r[3], "clasificacion": r[4], "medio": r[5]}
            for i, r in enumerate(source_rows, 1)
            if isinstance(r[0], datetime)
            and isinstance(r[8], (int, float))
            and day(r[0]) == day(p["fecha"])
            and money(r[8]) == money(p["importe"])
        ]
        aporte_matches = [
            {"fila": i, "referencia": r[2], "importe": r[3]}
            for i, r in enumerate(aporte_rows, 1)
            if isinstance(r[1], datetime)
            and isinstance(r[3], (int, float))
            and day(r[1]) == day(p["fecha"])
            and money(r[3]) == money(p["importe"])
        ]
        pdf = None
        if p["id"] in PDFS:
            rel, observation = PDFS[p["id"]]
            pdf = {**fingerprint(HERENCIA / "Comprobantes" / rel), "inspeccionVisual": observation}
        matrix.append(
            {
                **p,
                "fuenteMovs": source_matches,
                "candidatosAportesHistoricos": aporte_matches,
                "pdf": pdf,
                "candidatosBNA": candidates(banks, p),
                "candidatosGalicia": candidates(galicia, p),
                "candidatosExtractoCondominio": candidates(source_banks, p),
                "candidatosTarjetasPropias": candidates(cards, p),
                "candidatosSocio": candidates(socios, p),
                "candidatosCaja": candidates(cash, p),
                "vinculosCaja": [r for r in cash if r["pago"] == p["id"]],
            }
        )
    return {
        "fecha": datetime.now().isoformat(),
        "modo": "solo_lectura",
        "matriz": matrix,
        "fuentes": [fingerprint(p) for p in (source, aportes, extracto)],
        "totalPagos": sum(p["importe"] for p in payments),
        "totalAportesHistoricos": aporte_total,
        "registrosValores": values,
        "cuotasOperacionesTarjeta": read(
            "SELECT IdAuto,IdPagoTarjeta,IdOperacion,Importe,[Fecha Cuota] "
            "FROM dbo.[Cuotas Tarjetas de Credito] WHERE IdOperacion IN (554,956,995)"
        ),
        "socio3": read(
            "SELECT COUNT(*) filas,MIN(Fecha) inicio,MAX(Fecha) fin "
            "FROM dbo.MovimientosCuentaSocio WHERE IdSocio=3"
        ),
        "cuenta549": read(
            "SELECT SUM(Credito-Deuda) saldo FROM dbo.vw_MovimientosCuenta_Base "
            "WHERE IdContacto=549"
        ),
        "detalleOperacion485": read(
            "SELECT [Producto/Servicio],Cantidad,[Precio Unitario] "
            "FROM dbo.Det_Compras WHERE IdCompra=2143509478"
        ),
        "limites": (
            "Ventana de candidatos +/-5 días, importe exacto. No descarta pagos agrupados, "
            "cuotas, reintegros o apertura histórica. Sin tarjeta propia coincidente no se "
            "prueba pago ajeno. Ninguna conciliación ni escritura automática."
        ),
    }


if __name__ == "__main__":
    result = run()
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"rastreo-{datetime.now():%Y%m%d-%H%M%S}.json"
    target.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(f"15 pagos, ${result['totalPagos']}; evidencia: {target}")
