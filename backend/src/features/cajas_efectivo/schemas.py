"""Contratos de cajas de efectivo 027/038 — ver contracts/api.md."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from decimal import Decimal
from typing import Literal, Annotated
from pydantic import ConfigDict, Field, model_validator

CajaSlug = Literal["giamigli-sa", "campo-chica", "condominio-lsc", "giamigli-dolares"]
Moneda = Annotated[Decimal, Field(gt=0, max_digits=19, decimal_places=2)]
Identificador = Annotated[int, Field(gt=0)]


class Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AplicacionCaja(Estricto):
    tipoDocumento: Literal["CompraDeuda", "VentaHacienda", "VentaGranos", "Alquiler"]
    idDocumento: Identificador
    importeAplicado: Moneda


class BancoCaja(Estricto):
    medio: Literal["bna", "galicia", "mercado-libre"]
    idMovimiento: Identificador


class CompraParticularCaja(Estricto):
    idCompra: Identificador
    idSocio: Identificador
    idAsientoParticular: Identificador | None = None
    confirmarAsientoNuevo: bool = False


class RepartoCaja(Estricto):
    idRubro: Identificador
    idCentroCostos: Identificador
    idDestino: Identificador | None = None
    idCampania: Identificador | None = None
    idLote: Identificador | None = None
    importePesos: Moneda


class OperacionCaja(Estricto):
    tipo: Literal[
        "ingreso_dolares",
        "egreso_dolares",
        "pago",
        "cobro",
        "aporte",
        "retiro_a_cuenta",
        "retiro_ganancias",
        "traspaso_cajas",
        "extraccion_banco",
        "deposito_banco",
        "gasto_sin_comprobante",
        "retorno_sueldo_opcion_a",
    ]
    caja: CajaSlug
    fecha: date
    importe: Moneda
    concepto: str = Field(min_length=1, max_length=255)
    cuenta: Literal["A", "B"]
    idContacto: Identificador | None = None
    idSocio: Identificador | None = None
    cajaDestino: CajaSlug | None = None
    cajaContraparte: CajaSlug | None = None
    banco: BancoCaja | None = None
    intermediario: str | None = Field(default=None, min_length=1, max_length=255)
    evidencia: str | None = Field(default=None, min_length=1, max_length=255)
    motivoRelacionGiamigli: str | None = Field(default=None, min_length=1, max_length=255)
    compraParticular: CompraParticularCaja | None = None
    aplicaciones: list[AplicacionCaja] = Field(default_factory=list, max_length=100)
    repartos: list[RepartoCaja] = Field(default_factory=list, max_length=100)
    idSalario: Identificador | None = None

    @model_validator(mode="after")
    def validar_combinacion(self):
        if self.caja == "condominio-lsc" and self.tipo != "pago":
            raise ValueError("Condominio: los aportes/devoluciones se registran desde la caja de Giamigli con contraparte Condominio; aquí solo pagos directos de gastos de Giamigli.")
        es_usd = self.caja == "giamigli-dolares"
        if es_usd and self.tipo not in ("ingreso_dolares", "egreso_dolares", "aporte", "retiro_a_cuenta", "retiro_ganancias"):
            raise ValueError("Caja USD: elegir entrada/salida de dólares o aporte/retiro de socio.")
        if not es_usd and self.tipo in ("ingreso_dolares", "egreso_dolares"):
            raise ValueError("Entrada/salida de dólares requiere caja USD.")
        if any((target == "giamigli-dolares") != es_usd for target in (self.cajaDestino, self.cajaContraparte) if target):
            raise ValueError("No se admiten traspasos 1:1 entre pesos y dólares.")

        contacto = self.tipo in ("pago", "cobro")
        socio = self.tipo in ("aporte", "retiro_a_cuenta", "retiro_ganancias")
        bancario = self.tipo in ("extraccion_banco", "deposito_banco", "retorno_sueldo_opcion_a")
        if contacto != (self.idContacto is not None):
            raise ValueError("Solo pago/cobro requiere contacto.")
        if socio != (self.idSocio is not None):
            raise ValueError("Aporte/retiro requiere socio; otros tipos no admiten idSocio.")
        if bancario != (self.banco is not None):
            raise ValueError("Extracción/depósito/retorno requiere movimiento bancario.")
        if (self.tipo == "traspaso_cajas") != (self.cajaDestino is not None):
            raise ValueError("Solo traspaso_cajas requiere cajaDestino.")
        if self.cajaDestino == self.caja or self.cajaContraparte == self.caja:
            raise ValueError("Las cajas deben ser distintas.")
        if self.tipo == "traspaso_cajas" and "condominio-lsc" in (self.caja, self.cajaDestino):
            raise ValueError(
                "Condominio: registrar aporte/devolución del socio, no traspaso interno."
            )
        if self.cajaContraparte is not None:
            if self.tipo not in ("aporte", "retiro_a_cuenta") or self.idSocio != 3:
                raise ValueError(
                    "cajaContraparte solo aplica a aportes/devoluciones del Condominio."
                )
            if self.caja == "condominio-lsc" or self.cajaContraparte != "condominio-lsc":
                raise ValueError("Elegir caja de Giamigli y contraparte Condominio.")
        if self.aplicaciones and not contacto:
            raise ValueError("Solo pago/cobro admite aplicaciones.")
        if contacto and not self.aplicaciones:
            raise ValueError("Elegir los documentos que se pagan/cobran.")
        keys = [(a.tipoDocumento, a.idDocumento) for a in self.aplicaciones]
        if len(set(keys)) != len(keys):
            raise ValueError("Un documento no puede repetirse en aplicaciones.")
        if sum((a.importeAplicado for a in self.aplicaciones), Decimal(0)) > self.importe:
            raise ValueError("Las aplicaciones exceden el importe.")
        if contacto and sum((a.importeAplicado for a in self.aplicaciones), Decimal(0)) != self.importe:
            raise ValueError('La suma aplicada a documentos debe coincidir con el pago o cobro.')
        if self.tipo == "pago" and any(a.tipoDocumento != "CompraDeuda" for a in self.aplicaciones):
            raise ValueError("Un pago solo se aplica a compras.")
        if self.tipo == "cobro" and any(
            a.tipoDocumento == "CompraDeuda" for a in self.aplicaciones
        ):
            raise ValueError("Un cobro solo se aplica a documentos de venta/alquiler.")
        if self.compraParticular and (self.tipo != "pago" or self.caja == "condominio-lsc"):
            raise ValueError("Compra particular solo en pagos desde cajas de Giamigli.")
        if self.compraParticular and self.compraParticular.idCompra not in [
            a.idDocumento for a in self.aplicaciones
        ]:
            raise ValueError("La compra particular debe estar entre los documentos pagados.")
        if self.compraParticular and (
            len(self.aplicaciones) != 1 or self.aplicaciones[0].importeAplicado != self.importe
        ):
            raise ValueError(
                "Registrar la parte particular por separado, sin mezclar otras facturas."
            )
        gasto = self.tipo == "gasto_sin_comprobante"
        if gasto != bool(self.repartos):
            raise ValueError("Solo gasto sin comprobante requiere repartos.")
        if gasto and sum((r.importePesos for r in self.repartos), Decimal(0)) != self.importe:
            raise ValueError("Los repartos deben sumar el importe exacto.")
        if (self.tipo == "retorno_sueldo_opcion_a") != (self.idSalario is not None):
            raise ValueError("Solo retorno de sueldo requiere idSalario.")
        if self.tipo == "retorno_sueldo_opcion_a" and not self.evidencia:
            raise ValueError("El retorno de sueldo requiere evidencia.")
        if (self.intermediario or self.evidencia) and not bancario:
            raise ValueError("Intermediario/evidencia solo corresponde a movimientos bancarios.")
        if (
            "condominio-lsc" in (self.caja, self.cajaContraparte)
            and not self.motivoRelacionGiamigli
        ):
            raise ValueError("Indicar relación con Giamigli para operar Condominio.")
        return self


class ConfirmarOperacion(Estricto):
    operacion: OperacionCaja
    previewVersion: str = Field(pattern=r"^[0-9a-f]{64}$")
    advertenciasAceptadas: list[Literal["SALDO_NEGATIVO", "PERIODO_ARQUEADO"]] = Field(
        default_factory=list
    )


class AnularOperacion(Estricto):
    motivo: str = Field(min_length=1, max_length=255)
    versionEsperada: int = Field(ge=0)
    previewVersion: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    advertenciasAceptadas: list[Literal['SALDO_NEGATIVO','PERIODO_ARQUEADO']] = Field(default_factory=list)


class MovimientoCajaEfectivo(BaseModel):
    idMovimiento: int
    fecha: date
    concepto: str | None = None
    detalle: str | None = None
    importe: float
    cuenta: str | None = None
    formaPago: str | None = None
    numeroDocumento: str | None = None
    idContactoRelacionado: int | None = None
    idOperacion: int | None = None
    tipo: str | None = None
    anulada: bool = False
    saldoCorridoDecimal: str | None = None


class SaldoCaja(BaseModel):
    caja: str
    saldo: float
    saldoDecimal: str | None = None
    ultimoArqueo: dict | None = None
    cobertura: str | None = None


class MovimientosCajaResponse(BaseModel):
    items: list[MovimientoCajaEfectivo]
    page: int
    pageSize: int
    total: int
    saldoAnteriorDecimal: str | None = None
    subtotalFiltradoDecimal: str | None = None
