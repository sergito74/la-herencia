# Data Model: 043 — Rutina automática de documentos nuevos

Base: `WC`. Respaldo verificado antes de la migración (Constitución II). Script de esquema `backend/scripts/crear_esquema_rutina_043.py` (patrón de `crear_esquema_boveda_042.py`: `--verificar`, aplicar, `--revertir`).

## Rutina_Corridas

Una ejecución de la rutina.

| Campo | Tipo | Notas |
|---|---|---|
| IdRutinaCorrida | int identity PK | |
| Inicio, Fin | datetime2(0) | Fin NULL = en curso |
| Origen | nvarchar(20) | `programada` (única vía; `prueba` solo para la validación manual) |
| Estado | nvarchar(20) | `en_curso`, `ok`, `con_problemas`, `incompleta` |
| CuentasCorridas, CuentasConProblemas | int | |
| MailsLeidos, DocumentosNuevos, CargadosSolos, ParaCargarAMano | int | |
| Mensaje | nvarchar(400) | palabras simples |

Reglas: una sola fila `en_curso` a la vez; al arrancar el backend, una `en_curso` vieja pasa a `incompleta`.

## Rutina_Programacion

Fila única con los horarios (07:00 y 14:00) y la próxima corrida calculada.

| Campo | Tipo |
|---|---|
| Horarios | nvarchar(50) — `07:00,14:00` |
| ProximaCorrida | datetime2(0) |
| Activa | bit |

## Rutina_MarcaMails

Marca de lectura por almacén de Outlook.

| Campo | Tipo | Notas |
|---|---|---|
| Almacen | nvarchar(200) PK | nombre visible del almacén |
| UltimoRecibido | datetime2(0) | ReceivedTime del último mail procesado en una corrida completada |

La marca se adelanta solo al cerrar bien la corrida (si falla, la próxima reintenta desde la marca anterior; la deduplicación por adjunto evita dobles).

## DocumentosNuevos

Lo que entró por portal o mail, con su aviso y revisión.

| Campo | Tipo | Notas |
|---|---|---|
| IdDocumentoNuevo | int identity PK | |
| IdRutinaCorrida | int FK NULL | NULL si entró por una sincronización manual de la bóveda |
| Origen | nvarchar(10) | `portal` / `mail` |
| IdPortal | int NULL | si vino de portal (FK Portales) |
| IdDocumentoPortal | int NULL | FK Portales_Documentos |
| MailEntryId | nvarchar(200) NULL | si vino de mail |
| MailRemitente, MailAsunto | nvarchar(200) NULL | para mostrar el origen |
| MailRecibido | datetime2(0) NULL | |
| Sha256 | char(64) | único junto con Modulo (no dos avisos del mismo archivo) |
| Ruta | nvarchar(400) | archivo guardado |
| Tipo | nvarchar(30) | factura, nota_credito, nota_debito, boleta, retencion, liquidacion, recibo, resumen_banco, resumen_tarjeta, resumen_proveedor, contrato |
| Modulo | nvarchar(30) | `compras`, `impuestos`, `ventas`, `tesoreria`, `cuentas_corrientes`, `sin_clasificar` |
| IdContacto | int NULL | emisor (o cliente) |
| Fecha, Numero | date / nvarchar(50) NULL | del comprobante |
| Total | decimal(18,2) NULL | impreso |
| Estado | nvarchar(20) | `cargado_solo`, `para_cargar`, `ya_estaba` (no genera aviso) |
| Motivo | nvarchar(300) NULL | palabras simples (ej. "Emisor nuevo", "No cierra al centavo…") |
| IdRegistro | int NULL | id del registro creado/vinculado en su módulo (IdDeuda en Compras, etc.) |
| Revisado | datetime2(0) NULL | |
| RevisadoPor | nvarchar(60) NULL | |
| Creado | datetime2(0) default SYSDATETIME() | |

Reglas:
- Cuenta en el aviso: `Estado IN ('cargado_solo','para_cargar') AND Revisado IS NULL`.
- Un `para_cargar` que después se carga a mano conserva su estado, recibe `IdRegistro` y sigue esperando "Revisado" (la revisión es explícita).
- Cambiar el módulo de un `sin_clasificar` lo mueve de aviso; queda auditado.
- `ya_estaba`: el documento ya existía en el sistema; se registra para no reprocesarlo pero no avisa.

## Cambios a tablas existentes

- `Portales_Documentos.Revisado` (27/10/2026): se elimina (lo reemplaza `DocumentosNuevos`).
- `Portales`: el portal 21 (De Campo a Campo) recibe `CodigoConector = 'decampoacampo'` cuando el conector esté probado.
