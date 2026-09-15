# La Herencia - Memory for Claude Code

Fecha de actualización: 2026-09-15

## 1. Propósito del documento

Este archivo resume el contexto completo de la migración de los sistemas La Herencia para que Claude Code pueda continuar el trabajo sin perder decisiones, restricciones, rutas, estado del repositorio ni antecedentes.

El objetivo general es integrar el sistema productivo y administrativo de La Herencia en una aplicación web moderna, conectada exclusivamente a SQL Server, preservando los datos reales y migrando progresivamente los procesos de negocio, formularios, consultas, vistas e informes.

La aplicación final aprobada debe usar:

- Python para backend, APIs, automatización, integraciones, análisis y lógica de dominio.
- SQL Server como persistencia y fuente única de datos.
- Next.js para la aplicación web.
- TypeScript para el frontend.
- Tailwind CSS para estilos.
- TanStack Query para consultas, cache, sincronización e invalidación del estado remoto.

## 2. Usuario y autenticación

Usuario:

- Nombre: Sergio Giamberardini
- Email Git: sgiamberardini@gmail.com
- GitHub username: sergito74
- GitHub remoto: https://github.com/sergito74/la-herencia

Git Credential Manager quedó autenticado mediante navegador para la cuenta de GitHub `sergito74`.

No hay tokens, passwords ni secretos almacenados en este archivo.

## 3. Rutas principales

Workspace raíz:

`C:\Users\Sergio\Documents\La Herencia\Sistema La Herencia\La Herencia`

Sistema VB.NET original y prototipo actual:

`C:\Users\Sergio\Documents\La Herencia\Sistema La Herencia\La Herencia\La Herencia`

Proyecto web prototipo actual:

`C:\Users\Sergio\Documents\La Herencia\Sistema La Herencia\La Herencia\La Herencia.Web`

Repositorio Git interno:

`C:\Temp\LaHerencia.git\.git`

El workspace tiene un archivo `.git` puntero que apunta al repositorio interno:

`gitdir: C:/Temp/LaHerencia.git/.git`

Backup completo SQL Server:

`C:\Temp\LaHerencia_full_20260915_184255.bak`

Hash SHA-256 registrado del backup:

`E1CB952BA20AE7E013FF910C12F636786A...`

El hash completo puede volver a obtenerse con:

```powershell
Get-FileHash 'C:\Temp\LaHerencia_full_20260915_184255.bak' -Algorithm SHA256
```

## 4. Origen de los sistemas

El usuario tiene dos ubicaciones principales:

1. Sistema productivo/administrativo original:

`C:\Users\Sergio\Documents\La Herencia\Sistema La Herencia\La Herencia\La Herencia`

2. Repositorio documental administrativo:

`C:\Users\Sergio\Documents\La Herencia\Administracion y gestion`

La segunda ubicación no es otra solución ejecutable VB.NET. Es principalmente un repositorio documental con PDF, Excel, Word, imágenes y tres bases Access relacionadas con cuentas:

- `La Herencia - Cuentas.accdb`
- `La Herencia - Cuentas - bkp 19.03.2026.accdb`
- `La Herencia - Cuentas - bkp 15.09.2026.accdb`

El primer sistema contiene el proyecto VB.NET antiguo, muchas bases Access históricas, documentación, scripts de soporte y paquetes de consultas.

## 5. Regla de datos más importante

La aplicación debe trabajar exclusivamente con SQL Server.

Todas las referencias a Access, ACCDB, consultas locales, DataSet y TableAdapter se consideran obsoletas para la migración.

No usar para nueva funcionalidad:

- `*.accdb`
- `*.mdb`
- Access/OleDb
- consultas locales Access
- DataSet
- TableAdapter
- formularios Access como fuente de ejecución
- datos duplicados locales

La base de datos real está en SQL Server y debe ser consultada mediante backend/API. El navegador nunca debe conectarse directamente a SQL Server.

## 6. SQL Server

DSN existente:

`SQL_LaHerencia`

Configuración detectada:

- Driver: SQL Server
- Server: `LAPTOP-6MFRGTC3\SQLEXPRESS`
- Database: `LaHerencia`
- Authentication: `Trusted_Connection=Yes`

Cadena usada para pruebas locales:

```text
DSN=SQL_LaHerencia;Trusted_Connection=Yes;DATABASE=LaHerencia
```

Prueba de conexión realizada correctamente con ODBC.

La base respondió con:

- 175 tablas/vistas en el catálogo consultado.
- Aproximadamente 208 MB de tamaño de base al momento del backup.

Consultas de conexión PowerShell:

```powershell
$cs='DSN=SQL_LaHerencia;Trusted_Connection=Yes;DATABASE=LaHerencia'
$cn=New-Object System.Data.Odbc.OdbcConnection($cs)
$cn.Open()
$cn.Close()
```

## 7. Protección de datos reales

El usuario aclaró explícitamente que las tablas y datos son reales y no se pueden modificar ni eliminar.

Se creó un backup completo antes de continuar:

```sql
BACKUP DATABASE [LaHerencia]
TO DISK = N'C:\Temp\LaHerencia_full_20260915_184255.bak'
WITH COPY_ONLY, INIT, CHECKSUM, STATS=10
```

Se verificó con:

```sql
RESTORE VERIFYONLY
FROM DISK = N'C:\Temp\LaHerencia_full_20260915_184255.bak'
WITH CHECKSUM
```

Resultado:

`BACKUP_VERIFYONLY=OK`

Regla actual:

- Sistema en modo solo lectura.
- No ejecutar INSERT, UPDATE, DELETE, MERGE, TRUNCATE, ALTER, DROP ni procedimientos con efectos laterales.
- No realizar pruebas insertando datos reales.
- Si en el futuro se autorizan escrituras, exigir backup completo reciente y verificado, plan de rollback y confirmación explícita del usuario.

La API web actual tiene el endpoint POST de compras bloqueado con HTTP 403.
El botón WinForms de guardar compras también está bloqueado y muestra un mensaje de modo consulta.

## 8. Constitución Spec Kit

Archivo:

`.specify/memory/constitution.md`

Versión actual local:

`1.1.0`

Fecha de ratificación y última enmienda:

`2026-09-15`

Principios principales:

1. SQL Server es la fuente única de verdad.
2. Protección de datos reales es obligatoria.
3. Los procesos de negocio están antes que las tablas.
4. Toda información financiera y operativa debe tener significado y trazabilidad.
5. Cada módulo debe tener contrato SQL/API y pruebas.
6. Los agentes especialistas deben colaborar mediante supuestos, esquemas, fórmulas y criterios de aceptación.
7. Los cambios deben ser simples, revisables y reversibles.
8. El stack aprobado es Python + SQL Server + Next.js + TypeScript + Tailwind CSS + TanStack Query.

La constitución establece que no se debe introducir ASP.NET Core, JavaScript-only, otro framework frontend ni otra librería de estado remoto sin enmienda aprobada.

Importante: la constitución modificada está solamente local y todavía no fue committeada ni subida después de la enmienda tecnológica.

## 9. Git y GitHub

Repositorio remoto:

`https://github.com/sergito74/la-herencia.git`

Rama:

`main`

Baseline publicado originalmente:

- Commit inicial publicado: `720cebc13538310d76f6e375d44ccabe2d63624f`
- Mensaje: `chore: create migration baseline`
- Autor: `Sergio Giamberardini <sgiamberardini@gmail.com>`
- Rama local sincronizada con `origin/main` antes de modificar la constitución.

El commit anterior local antes de corregir autor era `8806716`; fue reemplazado por `720cebc` con el autor correcto.

Estado conocido al crear este archivo:

```text
main...origin/main
 M .specify/memory/constitution.md
```

`memory.md` es nuevo y debe agregarse en el próximo commit junto con la constitución actualizada, si el usuario lo autoriza o si el flujo de trabajo decide confirmar estos cambios.

Bases reales y backups no están en Git.

`.gitignore` excluye:

- `*.accdb`
- `*.mdb`
- `*.bak`
- `.vs/`
- `bin/`
- `obj/`
- archivos temporales
- entornos Python
- `node_modules/`
- `dist/`
- archivos de sesión y artefactos de Visual Studio

## 10. Spec Kit

Instalado desde el repositorio oficial de GitHub con release fijada:

```powershell
uv tool install specify-cli --from 'git+https://github.com/github/spec-kit.git@v1.0.7'
```

Versión instalada:

`specify-cli 1.0.7`

Prerrequisitos detectados:

- Windows
- Python 3.13.0
- uv 0.11.29
- Git 2.55.0.windows.1
- Node 24.16.0
- npm 12.0.1
- Visual Studio Code disponible

Verificación realizada:

```powershell
specify version
specify self check
specify check
```

Resultado: Spec Kit listo para usar.

Integración configurada: GitHub Copilot.
Script type: PowerShell.

Skills instaladas en:

`.github/skills/`

Skills:

- `speckit-constitution`
- `speckit-specify`
- `speckit-clarify`
- `speckit-plan`
- `speckit-tasks`
- `speckit-analyze`
- `speckit-implement`
- `speckit-converge`
- `speckit-checklist`
- `speckit-taskstoissues`

Flujo recomendado por módulo:

```text
/speckit-constitution
/speckit-specify
/speckit-clarify
/speckit-plan
/speckit-tasks
/speckit-analyze
/speckit-implement
/speckit-converge
```

Documentación local de Spec Kit:

`.specify/README.md`

## 11. Agentes especializados

Agentes guardados en `.github/agents/`:

1. `01-sql-server-engineer.agent.md`
   - SQL Server, T-SQL, esquema, vistas, rendimiento, seguridad e integridad.

2. `02-web-frontend-engineer.agent.md`
   - Frontend web, UX operativa, accesibilidad, responsive y APIs.

3. `03-python-engineer.agent.md`
   - Python, automatización, análisis, ETL de solo lectura, pruebas e integraciones.

4. `04-integrated-agro-management-engineer.agent.md`
   - Procesos integrados de administración, producción, sanidad, finanzas y tecnología.

5. `05-agricultural-production-specialist.agent.md`
   - Agricultura, ganadería, cultivos, campañas, labores, insumos, rendimiento y costos.

6. `06-livestock-health-specialist.agent.md`
   - Sanidad, bienestar, manejo, identificación, bioseguridad, vigilancia y trazabilidad ganadera.

7. `07-financial-direction-specialist.agent.md`
   - Dirección financiera, tesorería, cuentas corrientes, cobros, pagos, costos, flujo de fondos y controles.

8. `administracion-cuentas.agent.md`
   - Cuentas corrientes, proveedores, clientes, bancos, tarjetas, cobros, pagos y tesorería.

README de coordinación:

`.github/agents/README.md`

Orden de colaboración recomendado:

1. Integrador agropecuario define proceso y alcance.
2. Producción, sanidad y finanzas validan significado.
3. Especialista SQL define consultas, vistas y contratos.
4. Frontend implementa navegación y experiencia.
5. Python implementa auditorías, análisis, automatización y pruebas.

## 12. Entorno original VB.NET

Proyecto original:

`La Herencia/La Herencia.vbproj`

Inicialmente era una aplicación Windows Forms VB.NET antigua, Target Framework 4.5, con startup generado por `My Project` y dependencias Access/DataSet faltantes.

Se instaló:

- Visual Studio 2022 Build Tools.
- MSBuild 17.14.60.
- .NET Framework Developer Pack 4.8.1.

El proyecto VB fue actualizado temporalmente para compilar con .NET Framework 4.8.
Se creó `Program.vb` para reemplazar el punto de entrada faltante `My.MyApplication`.
Se eliminaron referencias de DataSet, TableAdapter, Access y `Administracion La Herencia.accdb`.

La compilación se validó usando salidas temporales:

```powershell
$msbuild='C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\MSBuild.exe'
& $msbuild '...\La Herencia.vbproj' /t:Build /p:Configuration=Debug /p:Platform=AnyCPU /p:BaseIntermediateOutputPath='C:\Temp\LaHerenciaObj\\' /p:OutputPath='C:\Temp\LaHerenciaBin\\' /v:minimal
```

Resultado: se generó `C:\Temp\LaHerenciaBin\La Herencia.exe`.

El cliente WinForms quedó como prototipo y modo solo lectura. No es el stack final aprobado.

## 13. Prototipo web existente: advertencia importante

Se creó un prototipo web en:

`La Herencia.Web/`

Tecnología real del prototipo actual:

- ASP.NET Core minimal API en C# / .NET 9.
- ODBC hacia SQL Server.
- HTML, CSS y JavaScript vanilla.
- Servido localmente con `dotnet`.

Esto fue una etapa exploratoria anterior. No coincide con el stack aprobado actualmente por la constitución, que exige:

- Python backend.
- Next.js.
- TypeScript.
- Tailwind CSS.
- TanStack Query.

Por tanto, el prototipo ASP.NET/vanilla debe considerarse temporal y debe migrarse o reemplazarse progresivamente. No agregar nueva funcionalidad importante en ASP.NET/vanilla salvo que el usuario modifique la constitución.

Publicación temporal usada:

`C:\Temp\LaHerenciaWebPublish`

URL local:

`http://localhost:5080`

El servidor se levantó varias veces en terminales persistentes. Verificar su estado antes de iniciar otra instancia para evitar conflictos de puerto.

## 14. Funcionalidad del prototipo web actual

El prototipo fue creado para entender el sistema usando datos reales en modo lectura.

Endpoints actuales principales en `La Herencia.Web/Program.cs`:

- `/api/dashboard`
- `/api/catalogs`
- `/api/purchases`
- `/api/purchases/{id}`
- `/api/operations`
- `/api/treasury`
- `/api/sql-objects`
- `/api/sql-preview`
- `/api/accounts`
- `/api/accounts/{id}`
- `/api/treasury/accounts`
- `/api/treasury/movements`
- `POST /api/purchases` está bloqueado con HTTP 403.

Funcionalidad visible implementada en el prototipo:

- Resumen con indicadores de compras, ventas de hacienda, ventas de granos y movimientos BNA.
- Compras con búsqueda y detalle.
- Operaciones con ventas de hacienda y ventas de granos.
- Tesorería con cuentas/cajas y movimientos filtrados.
- Cuentas corrientes con búsqueda por proveedor/cliente, tipo de contacto, saldos y movimientos.
- Datos SQL como explorador técnico de tablas/vistas y muestra de registros.
- Informes como accesos a lecturas de compras, operaciones y tesorería.

Datos comprobados en SQL Server durante el prototipo:

- 6.436 compras.
- 143 ventas de hacienda.
- 219 ventas de granos.
- 9.386 movimientos BNA.
- 175 tablas/vistas en el catálogo.
- 21 combinaciones de cuenta/caja en `Movimientos`.
- Proveedor `Rutas Sur Atlantico S.A.` con 4 movimientos de cuenta corriente.
- Selector probado: cuenta `Blue`, caja `La Herencia`.

## 15. Objetos SQL relevantes

Entidades:

- `dbo.Contactos`
  - `IdContacto`
  - `Tipo Contacto`
  - `Razon Social`
  - tipos encontrados: `Banco`, `Comprador`, `Consignatario`, `Empleado`, `Multiple`, `Organismo`, `Proveedor`, `Tarjeta de Credito`.

Cuenta corriente:

- `dbo.vw_MovimientosCuenta_Base`
- `dbo.vw_MovimientosCuenta_Saldo`

Campos relevantes:

- `Fecha`
- `IdContacto`
- `Razon Social`
- `Documento`
- `Nro Documento`
- `Deuda`
- `Credito`
- `Origen`
- `IdOrigen`
- `SaldoParcial` en la vista de saldo.

Compras:

- `dbo.Compras`
- `dbo.Det_Compras`
- `dbo.Rubros`

`Compras` incluye:

- `IdDeuda` identity
- `Fecha`
- `IdContacto`
- `Tipo documento`
- `Tipo`
- `Nro Documento`
- `Conceptos no gravados`
- `Ingresos Brutos`

`Det_Compras` incluye:

- `IdDetalleCompra` identity
- `IdCompra`
- `Cantidad`
- `Producto/Servicio`
- `IdRubro`
- `Precio Unitario`
- `IVA`

Tesorería:

- `dbo.Movimientos`
- `dbo.Resumen Cuenta`
- `dbo.Movimientos BNA`
- `dbo.Movimientos Galicia`
- `dbo.Pagos efectivo`
- `dbo.Valores propios`
- `dbo.Valores Recibidos`
- `dbo.Tarjetas`
- `dbo.Tarjetas_Resumenes`
- `dbo.Tarjetas_Resumenes_Lineas`

`Movimientos` tiene, entre otros:

- `IdMovimiento`
- `IdContacto`
- `Fecha`
- `Cuenta`
- `Caja`
- `Numero documento`
- `Importe imputado`
- `IdOperacion`

`Movimientos BNA` tiene:

- `IdMovimientoBNA`
- `Fecha / Hora Mov#`
- `Concepto`
- `Importe`
- `IdContacto`
- `Contacto`

`Movimientos Galicia` tiene:

- `IdMovimiento`
- `Fecha`
- `Descripción`
- `Débitos`
- `Créditos`
- `Saldo`
- `IdContacto`
- `Contacto`
- centro de costos, rubro y destino.

## 16. Historial de decisiones y correcciones

1. Se inspeccionaron ambas carpetas y se determinó que `Administracion y gestion` es principalmente documental, no otra aplicación ejecutable.
2. Se detectó que ambas bases Access enlazan al mismo SQL Server mediante DSN `SQL_LaHerencia`.
3. Se creó una capa VB `SqlServerData.vb` para conexión y lectura SQL.
4. Se agregó inicialmente un explorador de tablas/vistas.
5. Se migró `FrmComprasGrales` de ruta Access fija a SQL Server.
6. Se implementó temporalmente un alta transaccional de compras, pero luego se bloqueó por protección de datos reales.
7. Se creó listado de compras y detalle.
8. Se creó prototipo web para visualizar procesos.
9. Se detectó un problema de nombres JSON PascalCase vs JavaScript camelCase; se corrigió el frontend con helper `field` y/o serialización.
10. Se intentó agregar Cuentas corrientes y Tesorería; inicialmente el cambio no se publicó, luego se aplicó, compiló, publicó y verificó.
11. Se definieron agentes especialistas.
12. Se instaló Spec Kit.
13. Se creó la constitución Spec Kit.
14. Se creó línea base Git y se subió a GitHub.
15. Se actualizó la constitución para el stack Python/SQL Server/Next.js/TypeScript/Tailwind/TanStack Query.

## 17. Estado actual y pendientes inmediatos

Estado actual:

- GitHub remoto configurado y funcionando.
- `main` publicado.
- Baseline remoto: `720cebc`.
- Constitución actualizada localmente pero pendiente de commit/push.
- `memory.md` es este archivo y debe agregarse al siguiente commit.
- Base SQL Server intacta.
- Backup verificado disponible fuera de Git.
- Prototipo ASP.NET/vanilla funcionando como exploración, pero no es stack final.

Pendientes recomendados:

1. Crear/actualizar `memory.md` en el próximo commit y subirlo junto con la constitución.
2. Usar `/speckit-constitution` para revisar/ratificar si Claude Code necesita regenerar metadatos.
3. Usar `/speckit-specify` para el primer módulo acotado, recomendado:
   - Cuentas corrientes por proveedor/cliente.
   - Tesorería por banco/cuenta/caja.
   - Lectura de detalle y trazabilidad.
4. Ejecutar `/speckit-clarify` para resolver reglas de saldo, deuda, crédito y signos.
5. Ejecutar `/speckit-plan` con el stack Python + SQL Server + Next.js + TypeScript + Tailwind + TanStack Query.
6. Ejecutar `/speckit-tasks` y `/speckit-analyze` antes de implementar.
7. Crear backend Python nuevo, sin mezclarlo con el prototipo ASP.NET salvo que sea necesario durante transición.
8. Crear frontend Next.js con TypeScript, Tailwind y TanStack Query.
9. Mantener API y base en modo lectura hasta autorización explícita.
10. Añadir pruebas de contrato SQL/API, navegación y estados vacíos/error.
11. Hacer commit y push de la constitución `1.1.0` y este `memory.md`.

## 18. Cómo continuar con Claude Code

Abrir Claude Code en:

`C:\Users\Sergio\Documents\La Herencia\Sistema La Herencia\La Herencia`

Leer este archivo primero:

`memory.md`

Leer también:

- `.specify/memory/constitution.md`
- `.specify/README.md`
- `.github/agents/README.md`
- El agente especialista relevante de `.github/agents/`

No iniciar escrituras SQL.
No subir bases Access.
No usar ASP.NET/vanilla para nueva funcionalidad.
No asumir que el prototipo actual es la arquitectura final.

Primer ciclo recomendado:

```text
/speckit-specify Diseñar el módulo web de cuentas corrientes y tesorería en modo solo lectura, usando Python, SQL Server, Next.js, TypeScript, Tailwind CSS y TanStack Query. Debe permitir seleccionar proveedor/cliente, consultar saldo y movimientos trazables, seleccionar banco/cuenta/caja y revisar movimientos financieros. No modificar datos reales.
/speckit-clarify
/speckit-plan
/speckit-tasks
/speckit-analyze
/speckit-implement
/speckit-converge
```

## 19. Seguridad y advertencias para Claude Code

- No pedir ni imprimir tokens.
- No incluir credenciales en código.
- No ejecutar comandos destructivos.
- No ejecutar scripts de Access.
- No modificar SQL Server.
- No usar backups como fuente de lectura operacional.
- No versionar bases reales.
- Antes de cualquier escritura autorizada, detenerse y exigir backup SQL Server verificado.
- Si una consulta o columna no está confirmada, consultar `INFORMATION_SCHEMA.COLUMNS` y probar un SELECT limitado.
- Si existe una contradicción entre código previo y esta memoria/constitución, esta memoria refleja el contexto actual, pero la constitución es la autoridad normativa.
