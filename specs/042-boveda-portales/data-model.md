# Data Model: 042 — Bóveda de portales

Tablas nuevas en `WC`, creadas por `backend/scripts/crear_esquema_boveda_042.py` (idempotente, respaldo verificado antes, `--revertir`). Nombres nuevos, sin reutilizar tablas ajenas (ver memoria "WC tablas ajenas"). No se agregan columnas a tablas existentes.

## dbo.Boveda_Credenciales

| Campo | Tipo | Notas |
|---|---|---|
| IdCredencial | int IDENTITY PK | |
| Nombre | nvarchar(80) NOT NULL UNIQUE | ej. "Clave Fiscal Giamigli" |
| Titular | varchar(10) NOT NULL | `empresa` \| `socio` |
| IdSocio | int NULL | si Titular = socio |
| Usuario | nvarchar(120) NULL | visible (no secreto) |
| ClaveCifrada | varbinary(512) NULL | nonce+cifrado+tag, AAD `boveda:<Id>:clave` |
| ClaveActualizada | datetime2 NULL | |
| Rechazada | bit NOT NULL default 0 | el portal rechazó la clave en la última corrida; se limpia al cambiarla |
| Activo | bit NOT NULL default 1 | |

## dbo.Boveda_CredencialDatos

Datos adicionales de ingreso (CUIT, nro. cliente, PIN…).

| Campo | Tipo | Notas |
|---|---|---|
| IdDato | int IDENTITY PK | |
| IdCredencial | int FK | |
| Nombre | nvarchar(60) NOT NULL | UNIQUE (IdCredencial, Nombre) |
| Secreto | bit NOT NULL | |
| ValorTexto | nvarchar(200) NULL | solo si Secreto = 0 |
| ValorCifrado | varbinary(512) NULL | solo si Secreto = 1; AAD `boveda:<IdCredencial>:dato:<Nombre>` |

## dbo.Portales

| Campo | Tipo | Notas |
|---|---|---|
| IdPortal | int IDENTITY PK | |
| Nombre | nvarchar(80) NOT NULL UNIQUE | |
| Url | nvarchar(400) NOT NULL | enlace de acceso (http/https) |
| Tipo | varchar(12) NOT NULL | `organismo` \| `proveedor` \| `cliente` \| `banco` \| `otro` |
| IdContacto | int NULL | contacto del sistema para comparar saldo y cargar compras |
| IdCredencial | int NULL FK | varias filas pueden compartirla (FR-007) |
| CodigoConector | varchar(30) NULL | NULL = solo bóveda |
| Notas | nvarchar(1000) NULL | |
| Activo | bit NOT NULL default 1 | |

## dbo.Portales_Autorizaciones

| Campo | Tipo | Notas |
|---|---|---|
| IdAutorizacion | int IDENTITY PK | |
| IdPortal | int FK | |
| Alcance | varchar(30) NOT NULL | `solo_lectura_descarga` (único valor admitido) |
| AutorizadoPor | nvarchar(60) NOT NULL | |
| Fecha | date NOT NULL | fecha real de la autorización |
| Fuente | nvarchar(300) NULL | ej. "pedido 27/10/2026 (spec 042)" |
| RevocadaPor / Revocada | nvarchar(60) / datetime2 NULL | |

Vigente = la última fila sin `Revocada`. Sin vigente ⇒ no se entra (FR-008).

## dbo.Portales_Programacion

| Campo | Tipo | Notas |
|---|---|---|
| IdPortal | int PK FK | |
| Frecuencia | varchar(10) NOT NULL | `desactivada` \| `diaria` \| `semanal` \| `mensual` |
| DiaSemana | tinyint NULL | 1=lunes…7, si semanal |
| DiaMes | tinyint NULL | 1–28, si mensual |
| Hora | time(0) NOT NULL default '07:00' | |
| ProximaCorrida | datetime2 NULL | recalculada al guardar y al terminar cada corrida |
| Suspendida | bit NOT NULL default 0 | |
| MotivoSuspension | nvarchar(200) NULL | ej. "credenciales rechazadas 27/10 07:01" |

## dbo.Portales_Corridas

| Campo | Tipo | Notas |
|---|---|---|
| IdCorrida | int IDENTITY PK | |
| IdPortal | int FK | |
| Origen | varchar(12) NOT NULL | `programada` \| `manual` \| `migrada037` |
| Usuario | nvarchar(60) NULL | |
| Inicio / Fin | datetime2 | |
| Estado | varchar(24) NOT NULL | `en_curso` → `ok` \| `error` \| `requiere_intervencion` \| `credenciales_rechazadas` \| `sin_autorizacion` \| `sin_credenciales` \| `portal_cambio` \| `incompleta` \| `salteada` |
| Nuevos / Existentes / Cargados / Pendientes | int default 0 | |
| Mensaje | nvarchar(400) NULL | legible, nunca secretos |
| IdEjecucion037 | int NULL | trazabilidad de lo migrado |

## dbo.Portales_Documentos

Generaliza `DescargaPeajes_Documentos` (mismos estados y reglas de revalidación de 037).

| Campo | Tipo | Notas |
|---|---|---|
| IdDocumento | int IDENTITY PK | |
| IdPortal | int FK | UNIQUE (IdPortal, Clave) |
| Clave | varchar(160) NOT NULL | identificador estable en el portal |
| Tipo | varchar(20) NOT NULL | `factura` \| `nota_credito` \| `nota_debito` \| `resumen` \| `certificado` \| `boleta` \| `poliza` \| `liquidacion` \| `otro` |
| Proveedor | nvarchar(60) NOT NULL | parte del nombre `AAAAMMDD_Proveedor.pdf` |
| IdContacto | int NULL | |
| FechaDocumento | date NULL | |
| NumeroDocumento | varchar(30) NULL | |
| TotalImpreso | decimal(18,2) NULL | |
| Moneda | char(3) NULL | `ARS` \| `USD` |
| Ruta | nvarchar(400) NULL | carpeta de Compras del ejercicio |
| Sha256 | char(64) NULL | evita duplicar el mismo archivo bajado desde otro portal |
| IdCorrida | int NULL FK | |
| EstadoCarga | varchar(20) NOT NULL | `cargado_auto` \| `ya_cargado` \| `pendiente` \| `no_aplica` (no comprobante) \| `historico` |
| Motivo | nvarchar(300) NULL | |
| IdCompra | int NULL | |
| Creado | datetime2 default SYSDATETIME() | |

## dbo.Portales_EstadoCuenta / dbo.Portales_EstadoCuentaMovimientos

| Campo (cabecera) | Tipo | Notas |
|---|---|---|
| IdFoto | int IDENTITY PK | |
| IdPortal, IdCorrida | int FK | |
| IdContacto | int NULL | |
| FechaCorte | date NOT NULL | |
| Moneda | char(3) NOT NULL | una fila por moneda |
| SaldoPortal | decimal(18,2) NOT NULL | signo: positivo = deuda nuestra con el tercero |
| SaldoSistema | decimal(18,2) NULL | NULL si sin contacto o foto incompleta |
| Diferencia | decimal(18,2) NULL | al centavo; ≠ 0 ⇒ alerta (sin umbral) |
| Completa | bit NOT NULL | |
| Revisada | bit NOT NULL default 0 | el usuario marca que vio la diferencia; no cierra nada contable |

Movimientos: `IdMovimiento`, `IdFoto` FK, `Fecha`, `Comprobante nvarchar(60)`, `Detalle nvarchar(200)`, `Debe`, `Haber`, `Saldo decimal(18,2)`.

## dbo.Boveda_Auditoria

| Campo | Tipo | Notas |
|---|---|---|
| IdEvento | bigint IDENTITY PK | |
| Fecha | datetime2 default SYSDATETIME() | |
| Usuario | nvarchar(60) NULL | `sistema` para el planificador |
| Accion | varchar(30) NOT NULL | `alta_portal`, `edicion_portal`, `alta_credencial`, `cambio_clave`, `revelar`, `autorizar`, `revocar`, `programar`, `corrida`, `suspension` |
| IdPortal / IdCredencial | int NULL | |
| Detalle | nvarchar(400) NULL | sin valores secretos |

## Clave maestra (fuera de la base)

Administrador de credenciales de Windows, servicio `LaHerencia-Boveda`, cuenta `clave-maestra` (32 B, base64). Respaldo opcional en archivo `.lhkey` envuelto con frase de recuperación (R1).
