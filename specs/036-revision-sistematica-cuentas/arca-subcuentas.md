# Subcuentas de ARCA — ampliación autorizada 25/10/2026

Sergio pidió implementarlas antes de continuar la conciliación. Acceso desde la cuenta corriente del contacto 119, sin crear contactos nuevos ni otro libro contable.

## Comportamiento y aceptación

- Resumen y detalle por IVA; Ganancias y anticipos; retenciones de Ganancias efectuadas/SICORE; Autónomos Lucy; Autónomos Sergio; Autónomos sin titular identificado; Cargas sociales; Bienes Sustitutos; Otros impuestos; Por identificar.
- Cada movimiento conserva origen, identificador, fecha, deuda y crédito originales. Una clasificación distribuye el movimiento entre una o varias subcuentas; sus partes deben sumar exactamente deuda y crédito originales. No representa otro pago ni modifica el saldo de ARCA, bancos, cajas o socios.
- Clasificación automática solo por concepto explícito del original. Un VEP o débito genérico permanece por identificar. No deducir impuesto por importe. Autónomos sin beneficiario explícito quedan separados para revisar. Los aportes personales no generan otro gasto ni otro crédito al socio.
- Permitir clasificar/repartir con motivo obligatorio, conservar historia y usuario, controlar versión concurrente y volver al criterio automático. Los casos mixtos se reparten explícitamente, nunca se duplican.
- El detalle muestra el saldo propio de la subcuenta, apertura anterior al filtro y movimientos del período. Las tarjetas muestran saldo al corte; la suma coincide con el total sin redondear cada movimiento. El saldo es contable, no un crédito fiscal confirmado ni un cierre automático.
- No incorporar retenciones recibidas ya existentes en ventas como nuevos movimientos. Su conciliación fiscal sigue pendiente.

## Diseño, modelo y contrato

Backend `cuentas_corrientes/arca.py` y router independiente `/api/arca`; frontend `ArcaSubcuentas`, integrado en la cuenta corriente. Se usa Decimal y consultas conocidas parametrizadas. Nueva tabla append-only `ArcaClasificaciones`: versión identity, origen/IdOrigen, reparto JSON validado, motivo, usuario y fecha. Una fila con reparto vacío revierte al criterio automático. No se alteran tablas de origen ni vistas contables. Respaldo verificado antes del DDL.

`GET /api/arca/cuenta`: fechaDesde/fechaHasta opcionales, subcuenta opcional del catálogo, página/tamaño. Devuelve catálogo/resumen, saldo total al corte, apertura y saldo de la selección, cantidad total y filas paginadas con referencia al original, reparto y versión. Fechas invertidas: 422.

`PUT /api/arca/clasificacion`: origen, idOrigen, version, motivo y partes [{subcuenta,deuda,credito}], importes no negativos con hasta cuatro decimales. Reparto vacío = automático. Rechaza origen inexistente en ARCA (404), sumas incorrectas (422) y versión desactualizada (409). Usuario tomado de sesión; middleware existente impide escritura al rol Lectura. No se aceptan identificadores de otros contactos.

## Verificación requerida

Pruebas puras de conservación, reparto, saldo de apertura, precisión, fechas, clasificación ambigua y reversión; contrato con base simulada; esquema y lectura real sobre WC; compilación/lint focalizados y recorrido del navegador. Ninguna prueba automática escribe datos reales.
