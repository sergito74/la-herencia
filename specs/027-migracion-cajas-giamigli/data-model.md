# Data Model: Migración histórica de Cajas Giamigli

## 1. `MovimientosCuentaSocio` (existente, 021 — extendida)

Cambio aditivo, sin tocar filas existentes:

```sql
ALTER TABLE dbo.MovimientosCuentaSocio
    ADD ImporteUSD money NOT NULL CONSTRAINT DF_MovimientosCuentaSocio_ImporteUSD DEFAULT 0,
        ImporteKgCarne decimal(14,3) NOT NULL CONSTRAINT DF_MovimientosCuentaSocio_ImporteKgCarne DEFAULT 0;

ALTER TABLE dbo.MovimientosCuentaSocio DROP CONSTRAINT CK_MovimientosCuentaSocio_Importe;

ALTER TABLE dbo.MovimientosCuentaSocio
    ADD CONSTRAINT CK_MovimientosCuentaSocio_ImporteAlguno
    CHECK (Importe > 0 OR ImporteUSD > 0 OR ImporteKgCarne > 0);
```

| Columna | Tipo | Notas |
|---|---|---|
| `Importe` | money, NOT NULL, default 0 | Componente en pesos (antes era el único importe; ahora puede ser 0 si el movimiento es 100% USD/Kg carne) |
| `ImporteUSD` | money, NOT NULL, default 0 | **Nueva.** Componente en dólares |
| `ImporteKgCarne` | decimal(14,3), NOT NULL, default 0 | **Nueva.** Componente en Kg de carne (trueque) |
| `Medio` | nvarchar(60), NULL | Reutilizada para la "Forma Pago" de la planilla (ej. "Efectivo", "Supervielle", "Galicia") |
| `Motivo` | nvarchar(255), NULL | Proveedor/Servicio + Detalle de la planilla, concatenados |
| *(resto sin cambios)* | | `IdSocio`, `Tipo`, `Fecha`, `Origen`, `IdOrigen`, `Usuario`, `Anulada`, etc. — ver 021/data-model.md |

**Saldo por socio** (extiende `calcular_saldo` de 021): pasa a devolver 3 valores independientes —

```sql
SELECT
    SUM(CASE WHEN Tipo = 'AsignacionGasto' THEN Importe ELSE -Importe END) AS saldoPesos,
    SUM(CASE WHEN Tipo = 'AsignacionGasto' THEN ImporteUSD ELSE -ImporteUSD END) AS saldoUSD,
    SUM(CASE WHEN Tipo = 'AsignacionGasto' THEN ImporteKgCarne ELSE -ImporteKgCarne END) AS saldoKgCarne
FROM dbo.MovimientosCuentaSocio WHERE IdSocio = ? AND Anulada = 0
```

Sin conversión entre monedas — cada saldo se mantiene y se muestra por separado (spec FR-004, Clarifications).

## 2. `MovimientosCajaEfectivo` (nueva)

```sql
CREATE TABLE dbo.MovimientosCajaEfectivo (
    IdMovimiento      int            NOT NULL IDENTITY PRIMARY KEY,
    Caja              varchar(20)    NOT NULL,
    Fecha             datetime2      NOT NULL,
    Concepto          nvarchar(255)  NULL,
    Detalle           nvarchar(255)  NULL,
    Importe           money          NOT NULL,
    Cuenta            varchar(20)    NULL,
    FormaPago         varchar(60)    NULL,
    IdContactoRelacionado int        NULL,
    NumeroDocumento   nvarchar(60)   NULL,
    Usuario           varchar(60)    NOT NULL,
    FechaCarga        datetime2      NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT CK_MovimientosCajaEfectivo_Caja CHECK (Caja IN ('GiamigliSA', 'CampoChica'))
);

CREATE INDEX IX_MovimientosCajaEfectivo_Caja ON dbo.MovimientosCajaEfectivo (Caja, Fecha);
```

| Columna | Tipo | Notas |
|---|---|---|
| `Caja` | varchar(20) | `'GiamigliSA'` (hoja "Caja Efectivo Pesos") o `'CampoChica'` (hoja "Caja chica campo") |
| `Importe` | money, con signo | Positivo = ingreso a la caja, negativo = egreso. `Caja Efectivo Pesos` ya trae signo; `Caja chica campo` se normaliza como `Haber − Debe` al migrar |
| `Cuenta` | varchar(20), NULL | Solo aplica a `GiamigliSA` ("Blue"/"White"); NULL para `CampoChica` |
| `FormaPago` | varchar(60), NULL | Solo aplica a `CampoChica` (la hoja de Giamigli SA no tiene esta columna) |
| `IdContactoRelacionado` | int, NULL | Si el proveedor de la fila resolvió a un contacto existente (solo se usa para `GiamigliSA`, FR-008) |
| `NumeroDocumento` | nvarchar(60), NULL | Cuando la planilla lo tiene |

**Saldo por caja**: suma acumulada de `Importe` ordenada por `(Fecha, IdMovimiento)` — sin columna de saldo persistida, se calcula al leer (mismo criterio que `cuentas_socios.calcular_saldo`).

## 3. `MigracionCajasGiamigliRevision` (nueva)

```sql
CREATE TABLE dbo.MigracionCajasGiamigliRevision (
    IdRevision    int            NOT NULL IDENTITY PRIMARY KEY,
    Hoja          varchar(30)    NOT NULL,
    NumeroFila    int            NOT NULL,
    Motivo        nvarchar(255)  NOT NULL,
    DatosCrudos   nvarchar(max)  NULL,
    FechaCarga    datetime2      NOT NULL DEFAULT SYSUTCDATETIME(),
    Resuelto      bit            NOT NULL DEFAULT 0
);
```

| Columna | Notas |
|---|---|
| `Hoja` | Nombre de la hoja origen (ej. `"Cuenta Lucy"`, `"Caja Efectivo Pesos"`) |
| `NumeroFila` | Fila del Excel (1-indexed), para poder ubicarla en la planilla original si hace falta |
| `Motivo` | Por qué no se migró automáticamente (ej. `"Sin fecha"`, `"Sin ningún importe"`) |
| `DatosCrudos` | JSON con los valores originales de la fila, para no tener que reabrir el Excel |
| `Resuelto` | Marcado manualmente cuando una persona ya revisó el caso (no dispara ninguna migración automática al marcarse) |

## Relaciones y no-relaciones

- `MovimientosCuentaSocio.IdSocio` → `Socios.IdSocio` (ya existente, sin cambios).
- `MovimientosCajaEfectivo` no tiene relación obligatoria con ninguna otra tabla — `IdContactoRelacionado` es informativo/opcional, no una foreign key exigida (muchas filas de caja chica no van a resolver a ningún contacto, y eso es esperado, no un error).
- `MigracionCajasGiamigliRevision` no se relaciona con ninguna otra tabla — es una cola de trabajo independiente, no bloquea ni participa del cálculo de ningún saldo.
