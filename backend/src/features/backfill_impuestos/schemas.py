from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

Medio=Literal['bna','galicia','mercado-libre','efectivo','valores-propios','valores-recibidos']
class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')
class Existente(Strict):
    modo: Literal['existente']
    idTipoImpuesto: int=Field(gt=0)
class Generico(Strict):
    modo: Literal['generico']
class Decision(Strict):
    medio: Medio
    idMovimiento: int=Field(gt=0,le=2**63-1)
    accion: Literal['incluir','excluir']
    fuente: Literal['comprobante','generada']|None=None
    archivoId: str|None=Field(default=None,max_length=128)
    tipoImpuesto: Annotated[Existente|Generico,Field(discriminator='modo')]|None=None
    confirmacionDocumento: bool=False
    periodoLiquidado: str|None=Field(default=None,max_length=255)
    numeroDocumento: str|None=Field(default=None,max_length=255)
    @model_validator(mode='after')
    def included(self):
        if self.accion=='incluir':
            if self.fuente is None or self.tipoImpuesto is None:
                raise ValueError('Elegí fuente y tipo de impuesto')
            if self.fuente=='comprobante' and not (self.archivoId and self.confirmacionDocumento):
                raise ValueError('Abrí y confirmá el comprobante elegido')
            if self.fuente=='generada' and self.archivoId:
                raise ValueError('Una boleta generada no lleva archivo')
        return self
class Validar(Strict):
    organismoId: int=Field(gt=0)
    huellaFuente: str=Field(pattern=r'^[a-f0-9]{64}$')
    decisiones: list[Decision]=Field(min_length=1,max_length=200)
    @model_validator(mode='after')
    def unique(self):
        keys=[(d.medio,d.idMovimiento) for d in self.decisiones]
        if len(set(keys))!=len(keys): raise ValueError('Pagos repetidos')
        return self
class Confirmar(Validar):
    idLote: UUID
    huellaPropuesta: str=Field(pattern=r'^[a-f0-9]{64}$')
    preparacion: str=Field(max_length=4096)
    backupId: UUID
class TipoPatch(Strict):
    idTipoImpuesto: int=Field(gt=0)
    version: str=Field(pattern=r'^[a-fA-F0-9]{16}$')
class ArchivoPatch(Strict):
    archivoId: str=Field(max_length=128)
    version: str=Field(pattern=r'^[a-fA-F0-9]{16}$')
    confirmadoPorUsuario: Literal[True]
class Revertir(Strict):
    huellaReversion: str=Field(pattern=r'^[a-f0-9]{64}$')
    preparacion: str=Field(max_length=4096)
    backupId: UUID
