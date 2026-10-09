"""Respuestas y pedidos de la revisión sistemática de cuentas — 036 (contracts/revision-cuentas-api.md)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Cola = Literal["A", "B", "C", "D", "E", "F", "G", "H", "I"]
Etapa = Literal["E0", "E1", "E2", "E3", "E4", "E5", "E6"]
EstadoFicha = Literal["pendiente", "en-proceso", "esperando-evidencia", "esperando-sergio", "cerrada", "cerrada-con-excepcion"]
EstadoEfectivo = Literal["pendiente", "en-proceso", "esperando-evidencia", "esperando-sergio", "cerrada", "cerrada-con-excepcion", "reabierta"]
EstadoMarca = Literal["pendiente", "factura-cargada", "sin-documento", "anticipo"]
FuenteRespaldo = Literal["portal", "estado-de-cuenta", "pdf"]
FuenteSaldoExterno = Literal["portal", "pdf", "mail", "banco", "tarjeta", "sin-estado"]
Moneda = Literal["Pesos", "Dolares"]


# ---- Corte

class Corte(BaseModel):
    corte: date
    motivo: str | None = None
    usuario: str
    fecha: datetime


class CambioCorte(BaseModel):
    corte: date
    motivo: str | None = Field(default=None, max_length=200)


# ---- Tablero

class CasillaTablero(BaseModel):
    cola: Cola
    etapa: Etapa
    cuentas: int
    importe: float


class ComparacionTablero(BaseModel):
    semanaAnterior: date
    cerradasEnLaSemana: int
    variacionExcepciones: int


class TotalCola(BaseModel):
    cuentas: int
    importe: float


class Tablero(BaseModel):
    corte: date
    totalCuentas: int
    porEstado: dict[str, int]
    casillas: list[CasillaTablero]
    totalesPorCola: dict[str, TotalCola]
    comparacion: ComparacionTablero | None = None
    preguntas: int


class FotoTablero(BaseModel):
    idFoto: int
    semana: date
    corte: date
    fecha: datetime
    totalCuentas: int


class ListaFotos(BaseModel):
    total: int
    fotos: list[FotoTablero]


class Pregunta(BaseModel):
    idContacto: int
    razonSocial: str | None = None
    cola: Cola
    etapa: Etapa
    pregunta: str
    desde: datetime | None = None


# ---- Colas y lotes

class CuentaDeCola(BaseModel):
    idContacto: int
    razonSocial: str | None = None
    movimientos: int
    importe: float
    saldo: float
    moneda: Moneda
    etapa: Etapa
    estado: EstadoEfectivo
    otrosProblemas: list[str] = []


class ColaCuentas(BaseModel):
    cola: Cola
    total: int
    pagina: int
    cuentas: list[CuentaDeCola]


class ReglaLote(BaseModel):
    regla: str
    cola: Cola
    descripcion: str


class PedidoSimularLote(BaseModel):
    cola: Cola
    regla: str


class PedidoTildar(BaseModel):
    idsContacto: list[int] | None = None
    tildarTodas: bool = False


class CuentaDeLote(BaseModel):
    idContacto: int
    razonSocial: str | None = None
    tildada: bool
    cumple: bool = True
    saldoAntes: float | None = None
    saldoDespues: float | None = None
    detalle: str | None = None


class Lote(BaseModel):
    idCorreccion: int
    regla: str
    cola: Cola
    estado: Literal["simulada", "aplicada", "revertida", "descartada"]
    cuentas: list[CuentaDeLote]
    respaldo: str | None = None


# ---- Ficha

class Criterio(BaseModel):
    codigo: Literal["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
    etapa: Etapa
    cumple: bool | None = None  # None = no aplica
    medido: str
    texto: str
    evidencia: str | None = None  # por ejemplo "access" cuando C3 se cumple con la referencia del Access


class EntradaHistorial(BaseModel):
    accion: str
    detalle: str | None = None
    usuario: str | None = None
    fecha: datetime


class Antecedente035(BaseModel):
    estado: str
    nota: str | None = None
    fecha: datetime | None = None


class Cierre(BaseModel):
    corte: date
    saldoAlCierre: float
    usuario: str | None = None
    fecha: datetime | None = None
    conExcepcion: bool = False
    motivoExcepcion: str | None = None


class Ficha(BaseModel):
    idContacto: int
    razonSocial: str | None = None
    corte: date
    estado: EstadoFicha
    estadoEfectivo: EstadoEfectivo
    etapa: Etapa
    cola: Cola
    otrosProblemas: list[str] = []
    saldoAlCorte: float
    moneda: Moneda
    saldoEsperado: Literal["cero", "puede-tener-saldo"] | None = None
    criterios: list[Criterio]
    inventarioFuentes: list[dict] | None = None
    pagosSinFactura: int
    saldosExternos: int
    antecedente035: Antecedente035 | None = None
    fifoAplicadoAntes: bool = False
    pregunta: str | None = None
    cierre: Cierre | None = None
    historial: list[EntradaHistorial] = []


class CambioFicha(BaseModel):
    estado: Literal["en-proceso", "esperando-evidencia", "esperando-sergio", "cerrada", "cerrada-con-excepcion"]
    nota: str | None = Field(default=None, max_length=500)
    motivoExcepcion: str | None = Field(default=None, max_length=500)
    pregunta: str | None = Field(default=None, max_length=300)


class FuenteInventario(BaseModel):
    tipo: Literal["estado-proveedor", "extracto", "resumen-tarjeta", "certificado", "dropbox", "access"]
    disponible: bool
    detalle: str | None = None


class PedidoInventario(BaseModel):
    fuentes: list[FuenteInventario]


class Decision(BaseModel):
    idDecision: int
    tipo: Literal["descartar-access", "cierre-con-excepcion", "otro"]
    texto: str
    evidencia: str | None = None
    usuario: str | None = None
    fecha: datetime


class PedidoDecision(BaseModel):
    tipo: Literal["descartar-access", "cierre-con-excepcion", "otro"]
    texto: str = Field(min_length=1, max_length=500)
    evidencia: str | None = Field(default=None, max_length=500)


# ---- Pagos sin factura

class MarcaPago(BaseModel):
    estado: EstadoMarca
    nota: str | None = None
    idCompra: int | None = None
    fuenteRespaldo: FuenteRespaldo | None = None


class PagoSinFactura(BaseModel):
    medio: str
    idMovimiento: int
    fecha: date
    importe: float
    retencionAsociada: float | None = None
    importeEsperadoFactura: float
    fechaEsperadaDesde: date
    fechaEsperadaHasta: date
    confianza: Literal["alta", "media"]
    anteriorA2021: bool
    lado: Literal["proveedor", "cliente"] = "proveedor"
    marca: MarcaPago | None = None


class FacturaSinPago(BaseModel):
    origen: str
    idOrigen: int
    numero: str | None = None
    fecha: date
    importe: float
    lado: Literal["proveedor", "cliente"] = "proveedor"


class Consistencia(BaseModel):
    pagosSinFactura: float
    facturasSinPago: float
    saldo: float
    cierra: bool
    sinApertura: bool = False


class PagosSinFacturaCuenta(BaseModel):
    idContacto: int
    corte: date
    consistencia: Consistencia
    pagos: list[PagoSinFactura]
    facturasSinPago: list[FacturaSinPago]


class PedidoMarca(BaseModel):
    estado: EstadoMarca
    idCompra: int | None = None
    fuenteRespaldo: FuenteRespaldo | None = None
    nota: str | None = Field(default=None, max_length=500)


# ---- Evidencia externa

class SaldoExterno(BaseModel):
    idSaldoExterno: int
    fechaSaldo: date
    saldo: float
    moneda: Moneda
    fuente: FuenteSaldoExterno
    referencia: str | None = None
    nota: str | None = None
    saldoCuentaALaFecha: float
    diferencia: float
    clasificacion: Literal["cierra", "menor-al-umbral", "con-diferencia"]


class NuevoSaldoExterno(BaseModel):
    fechaSaldo: date
    saldo: float
    moneda: Moneda
    fuente: FuenteSaldoExterno
    referencia: str | None = Field(default=None, max_length=400)
    nota: str | None = Field(default=None, max_length=500)


# ---- Archivos de comprobantes

EstadoArchivo = Literal["comprobante-legible-extension-incorrecta", "no-legible", "vacio", "imagen-revisar"]


class ArchivoIncompleto(BaseModel):
    ruta: str
    periodo: str
    proveedor: str
    fecha: date | None = None
    estado: EstadoArchivo
    numero: str | None = None
    importe: float | None = None
    cargado: bool
    idCompra: int | None = None


class ArchivosIncompletos(BaseModel):
    raiz: str
    total: int
    archivos: list[ArchivoIncompleto]
