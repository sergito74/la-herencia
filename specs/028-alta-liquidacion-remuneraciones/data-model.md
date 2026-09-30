# Data Model: Alta de liquidación de remuneraciones

No se crea ninguna tabla ni columna nueva — la feature escribe sobre `dbo.Remuneraciones`, tabla existente hoy solo leída.

## Entidad: Liquidación de remuneraciones (`dbo.Remuneraciones`)

| Columna (SQL real) | Tipo | Alta | Notas |
|---|---|---|---|
| `IdSalario` | int, PK IDENTITY | autogenerado por SQL Server (confirmado `COLUMNPROPERTY(...,'IsIdentity')=1`) | no lo completa el usuario; se usa `OUTPUT INSERTED.IdSalario` para devolverlo tras el insert |
| `IdContacto` | int | requerido | FK lógica a `Contactos` (tipo `Empleado`); combo de búsqueda, nunca texto libre |
| `Fecha de pago` | datetime | requerido | fecha real de pago, puede ser futura (Edge Cases) |
| `Periodo liquidado` | nvarchar | requerido | texto libre; sugerido por defecto como "Mes Año" a partir de `Fecha de pago`, editable |
| `Sueldo basico` | money | opcional, default 0 | **haber** — suma en el neto |
| `Adic futuros aumentos` | money | opcional, default 0 | **haber** |
| `Ajuste` | money | opcional, default 0 | **haber** |
| `Vacaciones` | money | opcional, default 0 | **haber** |
| `Dia Gremio` | money | opcional, default 0 | **haber** |
| `Antiguedad` | money | opcional, default 0 | **haber** |
| `Ajuste No Remunerativo` | money | opcional, default 0 | **haber** |
| `Aguinaldo` | money | opcional, default 0 | **haber** |
| `Redondeo` | money | opcional, default 0 | **haber** |
| `Bonificacion adicional` | money | opcional, default 0 | **haber** |
| `Jubilacion` | money | opcional, default 0 | **descuento** — resta en el neto; se ingresa en positivo |
| `Ley 19032` | money | opcional, default 0 | **descuento** |
| `Obra Social` | money | opcional, default 0 | **descuento** |
| `Obra Social Acuerdos` | money | opcional, default 0 | **descuento** |
| `Aporte Sindical` | money | opcional, default 0 | **descuento** |
| `Servicio de Sepelio` | money | opcional, default 0 | **descuento** |
| `Recibo` | nvarchar | opcional | ruta relativa a `CARPETA_RECIBOS`, formato `Personal\Recibos\{año}\{archivo}.pdf` — solo se escribe si se adjuntó un PDF en esta alta o en una posterior |
| `IdOperacion` | int | no se toca | columna existente sin uso conocido (0/631 filas la tienen; no se le inventa semántica — Constitución Principio IV) |

### Campo derivado (no persiste, se muestra en pantalla)

- **Importe neto** = suma de los campos **haber** − suma de los campos **descuento** (ver `research.md` §1). Se recalcula en el momento (frontend, mientras se completa el formulario) y se devuelve también en la respuesta del alta para mostrarlo sin otro round-trip.

### Regla de duplicado (no bloqueante)

Antes de insertar: si existe una fila con el mismo `IdContacto` y el mismo texto exacto de `Periodo liquidado`, el alta responde con una advertencia explícita (ver `research.md` §3) — la persona confirma o cambia el período antes de reintentar.

## Entidad: Recibo (PDF)

No es una tabla — es un archivo en `CARPETA_RECIBOS/{año}/{año} {mes:02d} {Nombre Apellido}.pdf` (mismo `CARPETA_RECIBOS` ya definido en `repository.py`). Un archivo por liquidación. Su referencia vive en `Remuneraciones.Recibo` (ver arriba).

- `{año}` y `{mes}` salen de `Fecha de pago` de la liquidación.
- `{Nombre Apellido}` sale de `Contactos.[Razon Social]` del empleado elegido, tal cual (sin abreviar) — consistente con el patrón ya usado por los archivos "YYYY MM Nombre Apellido.pdf" del año más reciente (2026) en el histórico real.
- Si ya existe un archivo con ese nombre exacto (ej. se reintenta adjuntar), se sobreescribe — no se versiona.

## Entidad: Empleado (`dbo.Contactos`, `Tipo Contacto = 'Empleado'`)

Solo lectura desde esta feature — se usa el combo `ContactoSelect` ya existente (`tipoContacto="Empleado"`), sin alta ni edición de contactos.
