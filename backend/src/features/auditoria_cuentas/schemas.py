"""Esquemas de la auditoría de cuentas corrientes — 035 (contracts/auditoria-cuentas-api.md)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from src.features.cuentas_corrientes.schemas import Origen


class ParametrosAuditoria(BaseModel):
    plazoMaximoMeses: int
    umbralPesos: int
    anticipoDias: int


class CambioParametros(BaseModel):
    plazoMaximoMeses: int | None = None
    umbralPesos: int | None = None
    anticipoDias: int | None = None


class CausaResumen(BaseModel):
    causa: str
    cuentas: int
    importe: float
    excepcion: bool
    # grupos de imputaciones sospechosas: una cuenta puede estar en uno aunque su saldo coincida
    adicional: bool = False
    # solo para movimiento-sin-contacto: se cuentan movimientos, no cuentas
    movimientos: int = 0


class ResumenAuditoria(BaseModel):
    fechaCorte: date
    parametros: ParametrosAuditoria
    totalCuentas: int
    coinciden: int
    conDiferencia: int
    causas: list[CausaResumen]
    avisoCorte: str


class CuentaAuditada(BaseModel):
    idContacto: int
    razonSocial: str | None = None
    moneda: str
    saldoSistema: float
    saldoAccess: float | None = None
    diferencia: float | None = None
    sinExplicar: float = 0.0
    causa: str
    componentes: dict[str, float] = {}
    hallazgos: int = 0
    causasExtra: list[str] = []
    documentada: str | None = None


class Hallazgo(BaseModel):
    causa: str
    motivo: str
    importe: float | None = None
    medio: str | None = None
    idMovimiento: int | None = None
    fechaPago: date | None = None
    cantidadFacturas: int | None = None
    facturaMasVieja: date | None = None
    diasMaximos: int | None = None
    origenAplicacion: str | None = None
    idsAplicacion: list[int] = []


class EjemploMovimiento(BaseModel):
    medio: str
    idMovimiento: int
    fecha: date | None = None
    importe: float
    concepto: str | None = None


class ConceptoSinContacto(BaseModel):
    concepto: str
    movimientos: int
    importe: float
    neto: float
    ejemplos: list[EjemploMovimiento]


class ConceptoExplicado(BaseModel):
    clave: str
    movimientos: int
    importe: float


class Conocido(BaseModel):
    idConocido: int
    tipo: str
    clave: str
    importeRef: float | None = None
    motivo: str
    usuario: str | None = None
    activo: bool = True


class AltaConocido(BaseModel):
    tipo: str
    clave: str
    motivo: str
    importeRef: float | None = None


class GrupoCuentas(BaseModel):
    causa: str
    items: list[CuentaAuditada]
    total: int
    conceptos: list[ConceptoSinContacto] = []
    explicados: list[ConceptoExplicado] = []


class HallazgosCuenta(BaseModel):
    idContacto: int
    razonSocial: str | None = None
    hallazgos: list[Hallazgo]


class AvisoCuenta(BaseModel):
    tipo: str
    motivo: str
    importe: float | None = None


class CuentaVecina(BaseModel):
    idContacto: int
    razonSocial: str | None = None


class EntradaHistorial(BaseModel):
    id: int
    accion: str
    detalle: str | None = None
    usuario: str | None = None
    fecha: datetime | None = None


class RevisionCuenta(BaseModel):
    idContacto: int
    razonSocial: str | None = None
    moneda: str
    saldo: float
    gobierna: str = "Pesos"  # moneda que gobierna la cuenta: Pesos | Dolares | Mixta
    saldoEsperado: str | None = None
    estado: str  # pendiente | revisada | revision-vieja
    fechaRevision: datetime | None = None
    usuarioRevision: str | None = None
    nota: str | None = None
    saldoAlRevisar: float | None = None
    dificultad: int
    avisos: list[AvisoCuenta]
    siguiente: CuentaVecina | None = None
    anterior: CuentaVecina | None = None
    revisadas: int
    totalCuentas: int
    historial: list[EntradaHistorial] = []


class CambioRevision(BaseModel):
    estado: str | None = None
    nota: str | None = None
    saldoEsperado: str | None = None
    quitarSaldoEsperado: bool = False


class PedidoAnulacion(BaseModel):
    idsAplicacion: list[int]
    motivo: str


class PedidoNotaAjuste(BaseModel):
    tipo: str  # debito | credito
    fecha: date
    importe: float
    moneda: str = "Pesos"
    tipoDeCambio: float | None = None
    motivo: str


class CorreccionCuenta(BaseModel):
    idCorreccion: int
    regla: str
    estado: str
    usuario: str | None = None
    fecha: datetime | None = None
    detalle: str | None = None


class MovimientoRevision(BaseModel):
    fecha: date | None = None
    documento: str | None = None
    numeroDocumento: str | None = None
    moneda: str  # Pesos | Dolares: la moneda del documento; los pagos y cobros son siempre en pesos
    deudaOriginal: float
    creditoOriginal: float
    tipoDeCambio: float | None = None
    tcEstimado: bool = False
    deudaPesos: float
    creditoPesos: float
    saldoPesos: float
    saldoDolares: float
    origen: Origen
    origenTipo: str | None = None
    idOrigen: int | None = None


class MovimientosRevision(BaseModel):
    items: list[MovimientoRevision]
    total: int
    page: int
    pageSize: int
    saldoPesos: float
    saldoDolares: float
    tieneDolares: bool
    bimonetaria: bool
    gobierna: str  # Pesos | Dolares | Mixta
    saldoGobierna: float
    avisos: list[str]
