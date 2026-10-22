"""039: cuerpos de la API de pastaje. Importes Decimal (se reciben como string o número)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class TarifaBody(BaseModel):
    idTipoHacienda: int
    tipoTarifa: Literal["kg_novillo", "fijo_ars", "fijo_usd"] = "kg_novillo"
    valor: Decimal = Field(gt=0)
    vigenteDesde: date | None = None


class ContratoBody(BaseModel):
    idContacto: int
    fechaInicio: date
    fechaFin: date | None = None
    carpetaDocumentos: str | None = None
    archivoContrato: str | None = None
    clausulaInfraestructura: str | None = None
    clausulaSanidad: str | None = None
    clausulaMortandad: str | None = None
    otrasClausulas: str | None = None
    tarifas: list[TarifaBody] = Field(min_length=1)

    def model_dump(self, **kw):
        d = super().model_dump(**kw)
        d["tarifas"] = [{**t, "vigenteDesde": t["vigenteDesde"] or self.fechaInicio} for t in d["tarifas"]]
        return d


class ContratoUpdate(BaseModel):
    idContacto: int
    fechaInicio: date
    fechaFin: date | None = None
    carpetaDocumentos: str | None = None
    archivoContrato: str | None = None
    clausulaInfraestructura: str | None = None
    clausulaSanidad: str | None = None
    clausulaMortandad: str | None = None
    otrasClausulas: str | None = None
    tarifasNuevas: list[TarifaBody] = []
    version: int


class MovimientoBody(BaseModel):
    fecha: date
    tipo: Literal["ingreso", "egreso", "muerte", "faltante", "nacimiento", "destete", "recuento"]
    idTipoHacienda: int
    cabezas: int = Field(gt=0)
    numeroDte: str | None = Field(default=None, max_length=40)
    observacion: str | None = Field(default=None, max_length=400)


class AnularBody(BaseModel):
    motivo: str = Field(min_length=1, max_length=400)
    version: int


class FinalizarBody(BaseModel):
    fechaFin: date
    motivo: str = Field(default="Fin del contrato", max_length=400)
    version: int


class VersionBody(BaseModel):
    version: int


class PeriodoBody(BaseModel):
    desde: date | None = None
    hasta: date | None = None


class LiquidacionBody(BaseModel):
    periodo: str  # AAAA-MM


class IndiceManual(BaseModel):
    indice: Decimal = Field(gt=0)
    nota: str = Field(min_length=1, max_length=400)


class LeerComprobante(BaseModel):
    ruta: str = Field(min_length=1)


class ComprobanteBody(BaseModel):
    idContrato: int
    idLiquidacion: int | None = None
    idComprobanteAsociado: int | None = None
    tipo: Literal["factura", "nota_debito", "nota_credito"]
    letra: Literal["A", "B"]
    puntoVenta: int = Field(gt=0)
    numero: int = Field(gt=0)
    fecha: date
    vtoPago: date | None = None
    cae: str | None = Field(default=None, max_length=20)
    vtoCae: date | None = None
    cuitCliente: str | None = Field(default=None, max_length=11)
    periodoDesde: date | None = None
    periodoHasta: date | None = None
    detalle: str | None = Field(default=None, max_length=1000)
    neto: Decimal
    iva: Decimal
    total: Decimal = Field(gt=0)
    otrosTributos: Decimal = Decimal(0)
    archivoPdf: str | None = None
    aceptarAdvertencias: bool = False
