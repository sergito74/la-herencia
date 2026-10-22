# Research — 039 Contratos de pastaje

Relevamiento solo lectura del 22/10/2026 (consultas SELECT a WC y GET/POST de consulta a mercadoagroganadero.com.ar). Consulta previa a agentes 06 (hacienda), 07 (dirección financiera) y 01/04 (datos).

## R1. Fuente del índice INMAG
- **Decisión**: obtener el INMAG diario de `https://www.mercadoagroganadero.com.ar/dll/hacienda2.dll/haciinfo000011` (POST `txtFechaIni`/`txtFechaFin` dd/mm/aaaa, `USUARIO=SIN+IDENTIFICAR`), tabla "TOTALES POR DIA … I.N.M.A.G.". Guardar en tabla nueva `dbo.IndiceINMAG`. Reutilizar el patrón de `backend/scripts/cotizaciones_dolar_novillo.py` (función `novillo()`), cambiando URL y columnas.
- **Verificación**: 25/09/2026 = 4.068,212; 29/09/2026 = 4.241,828; 30/09/2026 sin índice ("-"). Promedio simple = 4.155,02 = liquidación real.
- **Rationale**: `IndiceNovillo` carga `haciinfo000013`, otro índice (25/09 = 4.166,214); no sirve para pastaje.
- **Alternativas**: reusar IndiceNovillo (rechazado: otro índice); total ponderado de la página 4.155,957 (rechazado: no es lo pactado).
- **Hallazgo lateral** (no se corrige en 039): `_num()` del script existente lee "6.316" como 6,316 → `IndiceNovillo.CabIngresadas` mal cargado. Para INMAG se usa un parser que trata '.' como miles.

## R2. Programación diaria
- **Decisión**: tarea de Windows "LaHerencia - Indice INMAG" diaria (`Register-ScheduledTask -Daily`, `-StartWhenAvailable -RunOnlyIfNetworkAvailable`), con instalador `backend/scripts/instalar_indice_inmag.ps1` según el precedente `instalar_descarga_peajes.ps1` (037). Cada corrida recupera los últimos 10 días faltantes (cubre feriados, PC apagada). Botón "Actualizar ahora" en la UI llama al mismo servicio.
- **Alternativas**: programador dentro del backend (rechazado: el backend no está siempre levantado).

## R3. Cuenta corriente y cobros
- **Decisión**: nueva rama `'Pastaje'` en `vw_MovimientosCuenta_Base` (factura y ND al debe del cliente, NC al haber); ampliar `CK_AplicacionesPago_TipoDocumento` con `'Pastaje'`; resolver documentos en `aplicaciones_pago/documentos.py` (como cuota de alquiler, 038); mapear origen en `recalculo_fifo/ejecuciones.py`; revisar `auditoria_cuentas/datos.py`, `bimonetaria.py` y `cajas_efectivo/operaciones.py`/`service.py`. Cobros con banco/caja/cheque existentes.
- **Retenciones sufridas**: registrar en `dbo.[Retenciones Ventas Hacienda]` (por contacto, ya entra a la vista y a OrigenMovimiento `ret-ventas-hacienda`) con referencia textual al comprobante de pastaje.
- **Gate**: comparar totales debe/haber de la vista antes/después de la migración (sin filas nuevas no debe cambiar nada), como en 038.

## R4. Campaña e imputación al resultado
- **Decisión**: la campaña se deriva del período: julio–junio, nombre "YYYY/YYYY+1" buscado en `dbo.Campañas` (existe 2026/2027 id 32). Establecimiento = `dbo.Establecimientos` id 1 La Herencia. El consolidado de campaña (`resultado_cultivo`) hoy no tiene ingresos ganaderos: se agrega una sección "Otros ingresos — Pastaje" por campaña/establecimiento, sin repartir a cultivos.

## R5. PDF
- **Generación**: reportlab (ya en requirements), patrón `ordenes/retiro_pdf.py`. Formato copia de "Liquidación de Pastaje - Septiembre.pdf". Destino: carpeta configurable por contrato, por defecto `C:\Users\Sergio\Documents\La Herencia\Ganaderia\Pastaje - La Herencia`; nombre `Liquidación de Pastaje - {Mes} {Año} - {Cliente}.pdf`; copia en almacenamiento de archivos del sistema.
- **Lectura de factura ARCA**: pdfplumber con lector propio siguiendo `descarga_peajes/lectores.py` (texto_pdf, numero, _buscar). Campos: tipo/código, punto de venta, número, fecha emisión, CUIT emisor (debe ser 30712114602), CUIT cliente, período desde/hasta, neto gravado, IVA 21%, total, CAE y vto. Verificado contra 20261006_Giamigli.pdf.

## R6. Datos maestros
- Ganadera San Justo (CUIT 30715943278) **no existe** en Contactos: alta desde la UI de contactos existente (o desde el alta del contrato) — no por script.
- Categorías: `[Tipo Hacienda]` (3 = Vaquillonas). Establecimientos: 1 La Herencia.

## R7. Cálculo y redondeo
- precio_promedio = round(promedio simple de INMAG de días con hacienda y con índice publicado, 2).
- kg_categoría = Σ tramos (cabezas × kg/cab/mes × días_tramo / días_del_mes), sin redondeo intermedio (Decimal).
- neto = round(Σ kg × precio_promedio, 2); IVA = round(neto × 0,21, 2); total = neto + IVA.
- Septiembre: 70 × 5 × 6/30 = 70 kg × 4.155,02 = 290.851,40; IVA 61.078,79; total 351.930,19. ✔
- Precio fijo (pesos/US$): neto = round(Σ cabezas-día × precio_mes / días_del_mes, 2); US$ con regla TC del comprobante.
