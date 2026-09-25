# Data Model: Cuentas corrientes de socios/directores y condominio

## Socios (tabla nueva)

| Columna | Tipo | Notas |
|---|---|---|
| IdSocio | int PK identity | |
| Nombre | varchar(100) NOT NULL | "Sergio", "Lucy", "Cond LSC", "Ceci" — catálogo cerrado, cargado una vez por script, sin alta/baja desde la UI en esta versión |

4 filas fijas al desplegar la feature. Sin FK física hacia `Contactos` — un socio no es un proveedor ni un cliente, es un catálogo propio (mismo criterio que otras tablas nuevas del sistema sin FK física entre sí).

## MovimientosCuentaSocio (tabla nueva)

| Columna | Tipo | Notas |
|---|---|---|
| IdMovimiento | int PK identity | |
| IdSocio | int NOT NULL | Referencia a `Socios.IdSocio` (sin FK física, mismo patrón que el resto del esquema) |
| Tipo | varchar(20) NOT NULL | `'AsignacionGasto'` (deuda del socio) \| `'Devolucion'` (crédito del socio) |
| Importe | money NOT NULL CHECK (Importe > 0) | Siempre positivo; el signo lo da `Tipo` (`AsignacionGasto` suma deuda, `Devolucion` la resta) |
| Fecha | datetime2 NOT NULL DEFAULT SYSUTCDATETIME() | |
| Origen | varchar(20) NULL | Solo para `AsignacionGasto`: `'CompraParticular'` en esta versión (diseñado extensible a futuros orígenes) |
| IdOrigen | int NULL | Solo para `AsignacionGasto`: `Compras.IdDeuda` de la compra particular de origen |
| Medio | varchar(60) NULL | Solo para `Devolucion`: medio de pago (efectivo, transferencia, etc.), texto libre |
| Motivo | nvarchar(255) NULL | Motivo/nota, requerido para `Devolucion`, opcional para `AsignacionGasto` |
| Usuario | varchar(60) NOT NULL | Quién generó el movimiento (mismo patrón que `AplicacionesPago.Usuario`) |
| Anulada | bit NOT NULL DEFAULT 0 | |
| MotivoAnulacion | nvarchar(255) NULL | Requerido si `Anulada = 1` |
| UsuarioAnulacion | varchar(60) NULL | |
| FechaAnulacion | datetime2 NULL | |

**Regla de inmutabilidad** (Clarifications, 2026-09-26): nunca se hace `UPDATE` de `Importe`/`Tipo`/`Origen`/`IdOrigen` sobre una fila existente. Corregir = anular (`Anulada=1` + motivo/usuario/fecha) e insertar una fila nueva si corresponde.

**Índices**:
- `(IdSocio)` para listar movimientos de un socio.
- Único filtrado: `(Origen, IdOrigen) WHERE Anulada = 0 AND Origen IS NOT NULL AND Tipo = 'AsignacionGasto'` — impide una segunda asignación vigente sobre el mismo origen (FR-009).

## AuditoriaReflejoSocio (tabla nueva, append-only)

| Columna | Tipo | Notas |
|---|---|---|
| IdAuditoria | int PK identity | |
| Accion | varchar(30) NOT NULL | `'Asignacion'` \| `'ReversionAsignacion'` \| `'Devolucion'` \| `'ReversionDevolucion'` |
| IdMovimiento | int NOT NULL | A qué fila de `MovimientosCuentaSocio` corresponde esta acción |
| IdSocio | int NOT NULL | Denormalizado a propósito, para poder auditar por socio sin joinear |
| Usuario | varchar(60) NOT NULL | |
| Fecha | datetime2 NOT NULL DEFAULT SYSUTCDATETIME() | |
| Detalle | nvarchar(255) NULL | Contexto libre (ej. "Compra particular Cumo Store, factura 0004-00000201") |

Nunca se actualiza ni se borra una fila de esta tabla — es el historial de auditoría en sí (research.md §2: decisión explícita del usuario de no reusar el patrón liviano de otras features).

## Entidades derivadas (calculadas, no persistidas)

- **Saldo de socio**: `SUM(CASE WHEN Tipo='AsignacionGasto' THEN Importe ELSE -Importe END) WHERE IdSocio = ? AND Anulada = 0`. Positivo = el socio le debe a la empresa; negativo = la empresa le debe al socio (saldo a favor, ver Edge Cases de la spec).
- **Importe bruto de una compra particular**: reutiliza la fórmula ya validada en `tarjetas_resumenes` (research.md §3) — se extrae a una función compartida en vez de duplicarse.

## Relación con features existentes

- **008/009 (`tarjetas_resumenes`)**: la fuente más común de compras "particular" que se van a asignar a un socio. Esta feature no modifica esas tablas, solo lee `Compras`/`Det_Compras` con la misma fórmula ya corregida (2026-09-26) para calcular el importe bruto.
- **019 (`aplicaciones_pago`)**: fuente del patrón de inmutabilidad/anulación reutilizado aquí (research.md §1).
- **016 (`auth`)**: `Usuario` se resuelve igual que en 019/020 (`NombreUsuario` de la sesión actual vía `AuthUsuarios`); sin restricción de rol adicional (Clarifications).
- **004 (`cuentas_corrientes`)**: la pantalla de consulta de un socio es análoga en espíritu (saldo + movimientos + origen), pero opera sobre `MovimientosCuentaSocio`/`Socios`, no sobre `Contactos`/`vw_MovimientosCuenta_Base` — no se modifica esa feature.
