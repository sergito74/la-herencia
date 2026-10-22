# Verificación de esquema 038

22/10/2026. Lecturas de metadatos y agregados sobre WC mediante conexión existente. Sin lecturas de LaHerencia ni cambios en Access.

## Columnas verificadas

| Tabla | Columna | Tipo | Longitud | Precisión/escala | Nullable |
|---|---|---|---|---|---|
| AjustesCuentaCorriente | IdAjuste | int | 4 | 10/0 | False |
| AjustesCuentaCorriente | IdContacto | int | 4 | 10/0 | False |
| AjustesCuentaCorriente | Fecha | date | 3 | 10/0 | False |
| AjustesCuentaCorriente | Lado | varchar | 10 | 0/0 | False |
| AjustesCuentaCorriente | Importe | money | 8 | 19/4 | False |
| AjustesCuentaCorriente | Motivo | nvarchar | 800 | 0/0 | False |
| AjustesCuentaCorriente | Usuario | nvarchar | 200 | 0/0 | False |
| AjustesCuentaCorriente | FechaAlta | datetime2 | 8 | 27/7 | False |
| Alquileres | IdAlquiler | int | 4 | 10/0 | False |
| Alquileres | Fecha | datetime | 8 | 23/3 | True |
| Alquileres | Inicio del periodo | datetime | 8 | 23/3 | True |
| Alquileres | Fin del periodo | datetime | 8 | 23/3 | True |
| Alquileres | IdContacto | int | 4 | 10/0 | True |
| Alquileres | Tipo de pago | nvarchar | 510 | 0/0 | True |
| Alquileres | Importe total del contrato | money | 8 | 19/4 | True |
| Alquileres | Retencion Ganancias | money | 8 | 19/4 | True |
| Alquileres | Cantidad de cuotas | smallint | 2 | 5/0 | True |
| Alquileres | Superficie total | real | 4 | 24/0 | True |
| Alquileres | Documento Original | nvarchar | -1 | 0/0 | True |
| Alquileres | IdOperacion | int | 4 | 10/0 | True |
| AplicacionesPago | IdAplicacion | int | 4 | 10/0 | False |
| AplicacionesPago | OrigenMovimiento | varchar | 20 | 0/0 | False |
| AplicacionesPago | IdMovimientoOrigen | bigint | 8 | 19/0 | False |
| AplicacionesPago | TipoDocumento | varchar | 20 | 0/0 | False |
| AplicacionesPago | IdDocumentoAplicado | int | 4 | 10/0 | False |
| AplicacionesPago | ImporteAplicado | money | 8 | 19/4 | False |
| AplicacionesPago | Fecha | datetime2 | 8 | 27/7 | False |
| AplicacionesPago | Usuario | varchar | 60 | 0/0 | False |
| AplicacionesPago | Anulada | bit | 1 | 1/0 | False |
| AplicacionesPago | MotivoAnulacion | nvarchar | 510 | 0/0 | True |
| AplicacionesPago | UsuarioAnulacion | varchar | 60 | 0/0 | True |
| AplicacionesPago | FechaAnulacion | datetime2 | 8 | 27/7 | True |
| AplicacionesPago | Origen | varchar | 30 | 0/0 | False |
| AplicacionesPago | NotaConciliacion | nvarchar | 510 | 0/0 | True |
| Detalle Cobro Alquiler | IdCobroAlquiler | int | 4 | 10/0 | False |
| Detalle Cobro Alquiler | IdAlquiler | int | 4 | 10/0 | True |
| Detalle Cobro Alquiler | Numero Cuota | smallint | 2 | 5/0 | True |
| Detalle Cobro Alquiler | Importe Cuota | money | 8 | 19/4 | True |
| Detalle Cobro Alquiler | Estado | nvarchar | 510 | 0/0 | True |
| Detalle Cobro Alquiler | Fecha vencimiento | datetime | 8 | 23/3 | True |
| MovimientosCajaEfectivo | IdMovimiento | int | 4 | 10/0 | False |
| MovimientosCajaEfectivo | Caja | varchar | 20 | 0/0 | False |
| MovimientosCajaEfectivo | Fecha | datetime2 | 8 | 27/7 | False |
| MovimientosCajaEfectivo | Concepto | nvarchar | 510 | 0/0 | True |
| MovimientosCajaEfectivo | Detalle | nvarchar | 510 | 0/0 | True |
| MovimientosCajaEfectivo | Importe | money | 8 | 19/4 | False |
| MovimientosCajaEfectivo | Cuenta | varchar | 20 | 0/0 | True |
| MovimientosCajaEfectivo | FormaPago | varchar | 60 | 0/0 | True |
| MovimientosCajaEfectivo | IdContactoRelacionado | int | 4 | 10/0 | True |
| MovimientosCajaEfectivo | NumeroDocumento | nvarchar | 120 | 0/0 | True |
| MovimientosCajaEfectivo | Usuario | varchar | 60 | 0/0 | False |
| MovimientosCajaEfectivo | FechaCarga | datetime2 | 8 | 27/7 | False |
| MovimientosCajaEfectivo | FilaPlanilla | int | 4 | 10/0 | True |
| MovimientosCajaEfectivo | IdPagoEfectivo | int | 4 | 10/0 | True |
| MovimientosCuentaSocio | IdMovimiento | int | 4 | 10/0 | False |
| MovimientosCuentaSocio | IdSocio | int | 4 | 10/0 | False |
| MovimientosCuentaSocio | Tipo | varchar | 20 | 0/0 | False |
| MovimientosCuentaSocio | Importe | money | 8 | 19/4 | False |
| MovimientosCuentaSocio | Fecha | datetime2 | 8 | 27/7 | False |
| MovimientosCuentaSocio | Origen | varchar | 20 | 0/0 | True |
| MovimientosCuentaSocio | IdOrigen | int | 4 | 10/0 | True |
| MovimientosCuentaSocio | Medio | varchar | 60 | 0/0 | True |
| MovimientosCuentaSocio | Motivo | nvarchar | 510 | 0/0 | True |
| MovimientosCuentaSocio | Usuario | varchar | 60 | 0/0 | False |
| MovimientosCuentaSocio | Anulada | bit | 1 | 1/0 | False |
| MovimientosCuentaSocio | MotivoAnulacion | nvarchar | 510 | 0/0 | True |
| MovimientosCuentaSocio | UsuarioAnulacion | varchar | 60 | 0/0 | True |
| MovimientosCuentaSocio | FechaAnulacion | datetime2 | 8 | 27/7 | True |
| MovimientosCuentaSocio | ImporteUSD | money | 8 | 19/4 | False |
| MovimientosCuentaSocio | ImporteKgCarne | decimal | 9 | 14/3 | False |
| Pagos efectivo | IdPagoEfectivo | int | 4 | 10/0 | False |
| Pagos efectivo | IdContacto | int | 4 | 10/0 | False |
| Pagos efectivo | IdTipoMovimiento | int | 4 | 10/0 | False |
| Pagos efectivo | IdFormaPago | int | 4 | 10/0 | True |
| Pagos efectivo | Fecha | datetime | 8 | 23/3 | True |
| Pagos efectivo | Cuenta | nvarchar | 510 | 0/0 | True |
| Pagos efectivo | Caja | nvarchar | 100 | 0/0 | True |
| Pagos efectivo | Numero documento | float | 8 | 53/0 | True |
| Pagos efectivo | Importe imputado | money | 8 | 19/4 | True |
| Pagos efectivo | IdOperacion | int | 4 | 10/0 | True |
| Pagos efectivo | Nro Mov | float | 8 | 53/0 | True |
| Remuneraciones | IdSalario | int | 4 | 10/0 | False |
| Remuneraciones | IdContacto | int | 4 | 10/0 | True |
| Remuneraciones | Fecha de pago | datetime | 8 | 23/3 | True |
| Remuneraciones | Periodo liquidado | nvarchar | 100 | 0/0 | True |
| Remuneraciones | Sueldo basico | money | 8 | 19/4 | True |
| Remuneraciones | Adic futuros aumentos | money | 8 | 19/4 | True |
| Remuneraciones | Ajuste | money | 8 | 19/4 | True |
| Remuneraciones | Vacaciones | money | 8 | 19/4 | True |
| Remuneraciones | Dia Gremio | money | 8 | 19/4 | True |
| Remuneraciones | Antiguedad | money | 8 | 19/4 | True |
| Remuneraciones | Ajuste No Remunerativo | money | 8 | 19/4 | True |
| Remuneraciones | Aguinaldo | money | 8 | 19/4 | True |
| Remuneraciones | Jubilacion | money | 8 | 19/4 | True |
| Remuneraciones | Ley 19032 | money | 8 | 19/4 | True |
| Remuneraciones | Obra Social | money | 8 | 19/4 | True |
| Remuneraciones | Obra Social Acuerdos | money | 8 | 19/4 | True |
| Remuneraciones | Aporte Sindical | money | 8 | 19/4 | True |
| Remuneraciones | Servicio de Sepelio | money | 8 | 19/4 | True |
| Remuneraciones | Redondeo | money | 8 | 19/4 | True |
| Remuneraciones | Bonificacion adicional | money | 8 | 19/4 | True |
| Remuneraciones | IdOperacion | int | 4 | 10/0 | True |
| Remuneraciones | Recibo | nvarchar | -1 | 0/0 | True |
| Socios | IdSocio | int | 4 | 10/0 | False |
| Socios | Nombre | varchar | 100 | 0/0 | False |
| TraspasosInternosTesoreria | IdEvento | int | 4 | 10/0 | False |
| TraspasosInternosTesoreria | MedioA | varchar | 20 | 0/0 | False |
| TraspasosInternosTesoreria | IdMovimientoA | bigint | 8 | 19/0 | False |
| TraspasosInternosTesoreria | MedioB | varchar | 20 | 0/0 | False |
| TraspasosInternosTesoreria | IdMovimientoB | bigint | 8 | 19/0 | False |
| TraspasosInternosTesoreria | Accion | varchar | 10 | 0/0 | False |
| TraspasosInternosTesoreria | Usuario | nvarchar | 200 | 0/0 | False |
| TraspasosInternosTesoreria | Fecha | datetime | 8 | 23/3 | False |

## Restricciones CHECK

- AplicacionesPago.CK_AplicacionesPago_Origen_Conciliacion: `([Origen]='fifo-032' OR [Origen]='correccion-031' OR [Origen]='automatica-mejor-esfuerzo' OR [Origen]='automatica-exacta' OR [Origen]='manual')`
- AplicacionesPago.CK_AplicacionesPago_Origen: `([OrigenMovimiento]='comp-venta-hacienda' OR [OrigenMovimiento]='comp-venta-granos' OR [OrigenMovimiento]='comp-compra' OR [OrigenMovimiento]='ret-ventas-hacienda' OR [OrigenMovimiento]='ret-iva-granos' OR [OrigenMovimiento]='retenciones' OR [OrigenMovimiento]='tarjetas' OR [OrigenMovimiento]='valores-propios' OR [OrigenMovimiento]='valores-recibidos' OR [OrigenMovimiento]='efectivo' OR [OrigenMovimiento]='galicia' OR [OrigenMovimiento]='bna')`
- AjustesCuentaCorriente.CK_ACC_Lado: `([Lado]='Credito' OR [Lado]='Deuda')`
- AjustesCuentaCorriente.CK_ACC_Importe: `([Importe]>(0))`
- TraspasosInternosTesoreria.CK_TraspasosInternosTesoreria_MedioA: `([MedioA]='valores-recibidos' OR [MedioA]='valores-propios' OR [MedioA]='efectivo' OR [MedioA]='mercado-libre' OR [MedioA]='galicia' OR [MedioA]='bna')`
- TraspasosInternosTesoreria.CK_TraspasosInternosTesoreria_MedioB: `([MedioB]='valores-recibidos' OR [MedioB]='valores-propios' OR [MedioB]='efectivo' OR [MedioB]='mercado-libre' OR [MedioB]='galicia' OR [MedioB]='bna')`
- TraspasosInternosTesoreria.CK_TraspasosInternosTesoreria_Accion: `([Accion]='Deshacer' OR [Accion]='Vincular')`
- MovimientosCuentaSocio.CK_MovimientosCuentaSocio_ImporteAlguno: `([Importe]>(0) OR [ImporteUSD]>(0) OR [ImporteKgCarne]>(0))`
- AplicacionesPago.CK_AplicacionesPago_TipoDocumento: `([TipoDocumento]='VentaGranos' OR [TipoDocumento]='VentaHacienda' OR [TipoDocumento]='CompraDeuda')`
- AplicacionesPago.CK_AplicacionesPago_Importe: `([ImporteAplicado]>(0))`
- MovimientosCajaEfectivo.CK_MovimientosCajaEfectivo_Caja: `([Caja]='CondominioLSC' OR [Caja]='CampoChica' OR [Caja]='GiamigliSA')`
- MovimientosCuentaSocio.CK_MovimientosCuentaSocio_Tipo: `([Tipo]='Devolucion' OR [Tipo]='AsignacionGasto')`

## Saldos y cardinalidad previos al DDL

```json
[
  {
    "Caja": "CampoChica",
    "cantidad": 100,
    "ultimo": 1247,
    "saldo": 96907.0
  },
  {
    "Caja": "CondominioLSC",
    "cantidad": 1226,
    "ultimo": 3353,
    "saldo": 0.23
  },
  {
    "Caja": "GiamigliSA",
    "cantidad": 2024,
    "ultimo": 2126,
    "saldo": 381785.15
  }
]
```

## Convenciones de efectivo (agregados)

```json
[
  {
    "IdTipoMovimiento": 1,
    "IdFormaPago": 3,
    "Caja": "La Herencia",
    "cantidad": 1305,
    "minimo": -2292.53,
    "maximo": 358400.0
  },
  {
    "IdTipoMovimiento": 1,
    "IdFormaPago": 3,
    "Caja": "Condominio",
    "cantidad": 172,
    "minimo": 10.0,
    "maximo": 811080.0
  },
  {
    "IdTipoMovimiento": 1,
    "IdFormaPago": 10,
    "Caja": "Particular L",
    "cantidad": 165,
    "minimo": 1.62,
    "maximo": 144093.79
  },
  {
    "IdTipoMovimiento": 1,
    "IdFormaPago": 10,
    "Caja": "Particular S",
    "cantidad": 96,
    "minimo": 64.32,
    "maximo": 80994.04
  },
  {
    "IdTipoMovimiento": 1,
    "IdFormaPago": 10,
    "Caja": "Condominio",
    "cantidad": 74,
    "minimo": 95.0,
    "maximo": 10004.7
  },
  {
    "IdTipoMovimiento": 3,
    "IdFormaPago": 24,
    "Caja": "La Herencia",
    "cantidad": 57,
    "minimo": -3915.32,
    "maximo": 17000.89
  },
  {
    "IdTipoMovimiento": 1,
    "IdFormaPago": 3,
    "Caja": "Particular S",
    "cantidad": 51,
    "minimo": 0.01,
    "maximo": 2244.0
  },
  {
    "IdTipoMovimiento": 4,
    "IdFormaPago": 3,
    "Caja": "Condominio",
    "cantidad": 49,
    "minimo": -3818.0,
    "maximo": -542.0
  },
  {
    "IdTipoMovimiento": 1,
    "IdFormaPago": 3,
    "Caja": "CampoChica",
    "cantidad": 47,
    "minimo": 800.0,
    "maximo": 90000.0
  },
  {
    "IdTipoMovimiento": 3,
    "IdFormaPago": 27,
    "Caja": "La Herencia",
    "cantidad": 46,
    "minimo": -81313.19,
    "maximo": -19.88
  },
  {
    "IdTipoMovimiento": 1,
    "IdFormaPago": 30,
    "Caja": "Particular L",
    "cantidad": 41,
    "minimo": 0.0,
    "maximo": 213160.0
  },
  {
    "IdTipoMovimiento": 2,
    "IdFormaPago": 30,
    "Caja": "Particular L",
    "cantidad": 41,
    "minimo": -395805.45,
    "maximo": -505.57
  },
  {
    "IdTipoMovimiento": 2,
    "IdFormaPago": 30,
    "Caja": "Particular S",
    "cantidad": 35,
    "minimo": -220000.0,
    "maximo": -1213.53
  },
  {
    "IdTipoMovimiento": 2,
    "IdFormaPago": 8,
    "Caja": "Ferias del Centro",
    "cantidad": 34,
    "minimo": -42496.1,
    "maximo": -66.08
  },
  {
    "IdTipoMovimiento": 1,
    "IdFormaPago": 3,
    "Caja": "GiamigliSA",
    "cantidad": 29,
    "minimo": 5000.0,
    "maximo": 700600.0
  },
  {
    "IdTipoMovimiento": 1,
    "IdFormaPago": 3,
    "Caja": "Ferias del Centro",
    "cantidad": 28,
    "minimo": 21.0,
    "maximo": 23814.0
  },
  {
    "IdTipoMovimiento": 3,
    "IdFormaPago": 16,
    "Caja": "La Herencia",
    "cantidad": 27,
    "minimo": -385384.34,
    "maximo": -377.56
  },
  {
    "IdTipoMovimiento": 3,
    "IdFormaPago": 19,
    "Caja": "J y M de La Serna",
    "cantidad": 22,
    "minimo": -301290.01,
    "maximo": -2435.12
  },
  {
    "IdTipoMovimiento": 3,
    "IdFormaPago": 19,
    "Caja": "La Herencia",
    "cantidad": 18,
    "minimo": -5566.0,
    "maximo": -21.0
  },
  {
    "IdTipoMovimiento": 1,
    "IdFormaPago": 15,
    "Caja": "La Herencia",
    "cantidad": 17,
    "minimo": -1726.25,
    "maximo": 280683.8
  },
  {
    "IdTipoMovimiento": 2,
    "IdFormaPago": 9,
    "Caja": "Ferias del Centro",
    "cantidad": 14,
    "minimo": -1276.55,
    "maximo": -31.2
  },
  {
    "IdTipoMovimiento": 1,
    "IdFormaPago": 9,
    "Caja": "J y M de La Serna",
    "cantidad": 13,
    "minimo": 5000.0,
    "maximo": 301290.01
  },
  {
    "IdTipoMovimiento": 1,
    "IdFormaPago": 15,
    "Caja": "J y M de La Serna",
    "cantidad": 13,
    "minimo": 25.5,
    "maximo": 6171.0
  },
  {
    "IdTipoMovimiento": 1,
    "IdFormaPago": 11,
    "Caja": "La Herencia",
    "cantidad": 11,
    "minimo": -2.5,
    "maximo": 29421.75
  },
  {
    "IdTipoMovimiento": 1,
    "IdFormaPago": 30,
    "Caja": "Particular S",
    "cantidad": 10,
    "minimo": 979.0,
    "maximo": 87540.0
  },
  {
    "IdTipoMovimiento": 1,
    "IdFormaPago": 4,
    "Caja": "La Herencia",
    "cantidad": 9,
    "minimo": 52.0,
    "maximo": 11079.45
  },
  {
    "IdTipoMovimiento": 2,
    "IdFormaPago": 7,
    "Caja": "Ferias del Centro",
    "cantidad": 9,
    "minimo": -79100.0,
    "maximo": -235.43
  },
  {
    "IdTipoMovimiento": 2,
    "IdFormaPago": 8,
    "Caja": "Particular S",
    "cantidad": 9,
    "minimo": -4250.62,
    "maximo": -2000.15
  },
  {
    "IdTipoMovimiento": 2,
    "IdFormaPago": 8,
    "Caja": "La Herencia",
    "cantidad": 8,
    "minimo": -27800.0,
    "maximo": -96.53
  },
  {
    "IdTipoMovimiento": 3,
    "IdFormaPago": 12,
    "Caja": "NC",
    "cantidad": 8,
    "minimo": -4.26,
    "maximo": 0.15
  }
]
```

## Módulos SQL que consumen efectivo

- `vw_MovimientosCuenta_Base`

## Claves y convenciones confirmadas

[{'tabla': 'AplicacionesPago', 'columna': 'IdAplicacion'}, {'tabla': 'MovimientosCajaEfectivo', 'columna': 'IdMovimiento'}, {'tabla': 'MovimientosCuentaSocio', 'columna': 'IdMovimiento'}, {'tabla': 'Pagos efectivo', 'columna': 'IdPagoEfectivo'}, {'tabla': 'TraspasosInternosTesoreria', 'columna': 'IdEvento'}]

Referencias FK: []

IdTipoMovimiento=1 Pago, 2 Cobro/Retiro; IdFormaPago=3 Efectivo. El signo físico de caja es negativo pago y positivo cobro; Corrección tras leer la definición completa de la vista: Pagos efectivo.[Importe imputado] es crédito directo: pago positivo y cobro negativo, opuesto al signo físico de caja. No reutilizar la sugerencia genérica por signo como prueba del libro. 038 usa aplicaciones explícitas. Sin IdPagoEfectivo duplicado en caja histórica.

Hallazgo: Pagos efectivo.IdContacto es NOT NULL; el puente bancario sin contacto requiere hacerlo nullable mediante DDL respaldado. No usar un contacto ficticio. Alquileres y Detalle Cobro Alquiler existen (10 contratos); AplicacionesPago restringe TipoDocumento a CompraDeuda/VentaHacienda/VentaGranos, por lo que el adaptador alquiler exige ampliar CHECK y fuente unificada, no solo el formulario.

## Inventario de consumidores Python

- `backend/src/features/auditoria_cuentas/datos.py`
- `backend/src/features/conciliacion_tesoreria/repository.py`
- `backend/src/features/cuentas_corrientes/origen_resolver.py`
- `backend/src/features/cuentas_corrientes/repository.py`
- `backend/src/features/recalculo_fifo/ejecuciones.py`
- `backend/src/features/recalculo_fifo/entrada.py`
- `backend/src/features/revision_cuentas/datos.py`
- `backend/src/features/tarjetas_cuenta/repository.py`
- `backend/src/features/tesoreria/repository.py`
- `backend/src/features/traspasos_internos_tesoreria/repository.py`
- `backend/src/features/vinculos/fuente.py`

Estrategia: vista vw_PagosEfectivoVigentes excluye pagos creados por operaciones anuladas; consumidores de lectura se dirigen a ella, preservando tabla física y registros para auditoría. vw_MovimientosCuenta_Base consume esa vista y excluye bancos vinculados a operaciones 038 vigentes mediante BancoOperacionCaja (incluida conciliación de tesorería). Anular libera la exclusión; no modifica importes/contactos bancarios históricos ni reasignaciones. Cancelar aplicaciones propias antes de marcar operación, rechazar aplicaciones ajenas. No afectar traspasos 024 anteriores a 038.

Centro de costos no tiene PK/índice único: relación validada por aplicación sin FK física. Primer intento DDL falló por esa referencia y se revirtió completo; segundo intento corregido respaldado y aplicado.

## Ampliación de evidencia de lectores y anulaciones
- IdFormaPago=30 no existe en Formas de pago - retiro, aunque hay referencias históricas; nota interna nueva Particular usa NULL sin modificar historia. Pago físico 1/3 y cobro 2/3 mantienen signos contables correctos.
- revisión_cuentas/datos.py sumaba AjustesCuentaCorriente directamente; se agregó exclusión de AjusteNoCobrado propio de operación anulada, igual que la vista central. Validación de salario permite volver a operar tras anulación sin contar el ajuste anterior como vigente.
- Referencias verificadas para impedir anulaciones parciales: ReasignacionesContacto (Origen/IdOrigen), PagosSocioProveedor (IdMovimientoSocio), Tarjetas_Resumenes_Pagos (Origen/IdMovimientoOrigen). Se bloquean dependencias ajenas, no se borran.
- IdOperacionCaja es el vínculo nuevo en MovimientosCajaEfectivo; no reutiliza el IdOperacion int heredado de Pagos efectivo. Un índice UNIQUE filtrado sobre IdPagoEfectivo de movimientos nuevos vigentes asegura un solo efecto físico.
