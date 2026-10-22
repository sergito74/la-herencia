# Avance conciliaciones — 22/10/2026 (traspaso a Codex)

> **Punto de entrada vigente para continuar la cuenta 375:** [pendientes y resumen](sergio-375-pendientes-resumen-20261022.md). Leer también la sección 4 de este documento: registra las acciones y respuestas posteriores al traspaso inicial y corrige hipótesis de las secciones anteriores. Los identificadores P/S se conservan en el [detalle histórico](sergio-375-pagos-para-revisar-20261022.md).

Continúa [avance-conciliaciones-20261021.md](avance-conciliaciones-20261021.md). Reglas vigentes: escribir solo en WC; Access es solo referencia; scripts re-corribles con `backup_verificado` + `reconciliation_transaction`; push a `main` autorizado.

## 1. Hecho el 22/10

### Cotizaciones y BNA
- `scripts/cotizaciones_dolar_novillo.py`: tablas `dbo.[Dolar BNA]` y `dbo.IndiceNovillo` en WC desde sus fuentes (errepar, Mercado Agroganadero). Reemplaza "Parametros financieros.xlsx".
- El lanzador (`launcher/LaHerencia.ps1`) lo corre una vez por día al abrir, en segundo plano (`launcher/.run/cotizaciones.ok`, logs `cotizaciones*.log`).
- BNA (369): intereses por cuota (`banco_nacion_intereses_cuotas_036.py`, comprobantes `INT369-aammdd`). Queda el capital de $137.500 del préstamo 0019136529, que vence el 22/02/2027.

### Cuentas de socios (`MovimientosCuentaSocio`; socio 1 = Sergio, 2 = Lucy)
- Mutuo de Lucy de 2018: US$ 27.000 más 9% anual, solo en dólares, a favor de Lucy (`mutuo_lucy_2018.py`). Se vuelve a correr después de cada 20/08.
- `socios_valuacion_036.py`:
  - Anula 46 duplicados de la revisión.
  - NC de Allianz por $105.
  - Valoriza los movimientos sin valuación: 50% kg novillo + 50% US$; antes del 16/03/2020, 100% US$.
- Cumo Store: compra particular de Sergio pagada con la Visa Galicia de Giamigli (`cumo_store_deuda_sergio_036.py`).
- Particulares de 2020-2022 revisados uno por uno (`socios_particulares_036.py`, `socios_carrefour_lucy_036.py`):
  - Irma de marzo de 2021 (Lucy).
  - Ebox (Sergio).
  - Mori $8.214 según el extracto del ICBC.
  - Carrefour 30/10/2020: el Haber de $4.284,23 de la planilla era un error.
- 46 pagos Particular L/S de 2011-2019 cargados en 100% US$ (`socios_particulares_pre2020_036.py`).
- Retiro de efectivo de Sergio del 28/11/2022 por $18.500: en la caja figuraba como recibos 5 (Mori) y 6 (Franco), que en realidad se pagaron por transferencia el 02/12 (`socios_retiro_sergio_20221128_036.py`).
- Franco (379) y Mori (376), 2022:
  - Sueldo = neto del recibo formal.
  - La diferencia ($2.659, $979 y $2.599) la pagó Sergio en efectivo.
  - Nunca usar bonificaciones negativas.
  - Scripts: `franco_mori_sueldos_2022_036.py` y `franco_mori_pagos_sergio_2022_036.py`.
  - Las dos cuentas quedan en 0.
- Planilla `Cajas Giamigli.xlsx`, corregida con Excel COM (hay backups en `backups/Cajas Giamigli-20261022-*.xlsx`):
  - Fila de Cumo Store.
  - Fórmulas K/L de "Cuenta Lucy" (filas 268 y 297) y N144.
  - Filas nuevas: Irma, Ebox, retiro de Sergio y pagos de Sergio a Franco/Mori.
  - Mori $8.214.
  - Caja 28/11/2022 renombrada como retiro.
  - **Al editar con COM, verificar `Workbook.ReadOnly`**: si Sergio la tiene abierta, el guardado falla en silencio. No usar funciones de PowerShell para asignar `Value2`: falla el cast; usar `Range("B12").Value2`.
- Saldos de los socios al 22/10, a favor del socio:

  | Socio | kg novillo | US$ | Mutuo |
  |---|---|---|---|
  | Sergio | 4.173,69 | 7.461,21 | — |
  | Lucy | 920,11 | 134,50 | US$ 46.440 |

### Sistema
- Pantalla de Cuentas de socios: deuda actualizada (kg × novillo + US$ × dólar de hoy), con el mutuo aparte (`cuentas_socios/repository.py` `deuda_actualizada`, `SociosListado.tsx`, `CuentaSocio.tsx`).
- Listado de saldos de Cuentas corrientes sin ventana sobre `vw_MovimientosCuenta_Saldo` (`get_saldos_todos`). Antes llegaba a tardar 7 minutos.

## 2. PENDIENTE (en este orden)

1. **Reiniciar el sistema** (`launcher\LaHerencia.ps1 -Stop` y volver a abrir) para que el backend tome los cambios del 22/10. El frontend ya está compilado.
2. **Lentitud / SQL Server sin memoria.** La PC tiene 12 GB con unos 700 MB libres, y SQL Express quedó con ~146 MB y esperas `RESOURCE_SEMAPHORE`; conectarse llegó a tardar 50-100 s. Propuesta sin aplicar: `min server memory` = 1024 MB. **Pedir autorización a Sergio antes.**
3. **Cuenta de Sergio, contacto 375 (Sergio pidió revisarla con cuidado, "es compleja").** Sin ficha de revisión; saldo de la vista +$8.688.657 (pagos > sueldos registrados).
   - Sueldos registrados 2011-2026: $59,4 M. Pagos: $68,1 M.
   - 113 pagos coinciden exactamente con un sueldo.
   - 58 pagos ($6,8 M) también están en la cuenta de socio y hoy cuentan dos veces: "Devolución por aporte pagos varios" $3,4 M, Allianz Taos $2,2 M, aportes y préstamos, retiros.
   - 38 pagos sin contraparte ($8,49 M):
     - 2011-2017: $187.500. Parecen retiros; hay comprobantes en `Cuentas a pagar\Transferencias\Sergio Giamberardini`.
     - 2021-2023: $620.000.
     - Abril-noviembre de 2024: ~$700.000 por mes, con retención de Ganancias (certificados en `Cuentas a pagar\Certificados Retenciones\2024`). **¿Honorarios de director sin comprobante?**
     - 2025-2026: $3,0 M.
   - La hoja "Sueldo Sergio" de Cajas Giamigli: desde 2023 el sueldo se pacta en 250 kg novillo + US$ 550 por mes, aparte del recibo formal.
   - Preguntas para Sergio:
     - (a) ¿Las transferencias de 2024 con retención son honorarios?
     - (b) ¿Las transferencias sueltas son retiros?
     - (c) ¿Qué manda: el recibo formal o los 250 kg + US$ 550? ¿La diferencia va a la cuenta de socio?
   - Objetivo: el 375 con solo sueldos y honorarios (cierra en 0), y todo lo demás en la cuenta de socio.
   - Script de análisis usado: ver la sección 3.
4. **Contactos 375/390 y Allianz:** devolver a Allianz los débitos reasignados al 375 (y los 2 asignados a AFIP 119). Los reintegros y retiros del Condominio se cuentan dos veces en 375/390. Depende del punto 3.
5. **Condominio LSC (549 / socio 3), en pausa:** los aportes 2011-2016 por $733.781 ("Aportes de Capital Directores.xlsx") son del Condominio para fondear el BNA. Van a su cuenta, no a Sergio ni a Lucy, y no duplican los pagos Particular L/S.
6. **Planilla:** los 46 pagos de antes de 2020 no se agregaron a Cajas Giamigli. Preguntar si los quiere ahí.
7. **Siguiente cuenta: AFIP (119).** Virginia (564) sigue en pausa.
8. **Para el final** (de `avance-conciliaciones-20261021.md` §5): criterio C3 de Access en las fichas; 5 tests que dependen de datos reales; 56 PDF de compras sin archivo.

## 3. Cómo se analizó el 375

Separar los pagos de la vista `vw_MovimientosCuenta_Base` (IdContacto 375) en tres grupos:
1. Pagos iguales a un sueldo (`Remuneraciones`, mismo importe, ±40 días).
2. El resto, comparado con `MovimientosCuentaSocio` socio 1 (mismo importe, ±10 días).
3. Lo que queda sin contraparte.

Los sueldos de Access son recibo formal + "Bonificación adicional" (la parte informal) en `dbo.Remuneraciones`.

## 4. Retoma de Codex y respuestas de Sergio (22/10/2026)

- Aplicación reiniciada: `/health` devolvió `ok` y frontend HTTP 200.
- Sergio autorizó `min server memory (MB) = 1024`, pidiendo reconfirmar el diagnóstico.
- Reconfirmación: RAM física 12.356.816 KB; disponible 836.872 KB; SQL Server Express 17.0.1000.7 usaba 226.840 KB y marcaba `process_physical_memory_low = 1`. Esperas acumuladas RESOURCE_SEMAPHORE: 128, por 3.822.938 ms; sin consultas esperando en esa muestra. Conexión inicial: 0,07 s. Esto respalda presión de memoria e historial de esperas, pero no reproduce en este momento conexiones de 50–100 s ni prueba que sea la única causa de lentitud.
- Aplicado con `sp_configure` y `RECONFIGURE`: mínimo anterior configurado 0 (en uso 16); nuevo configurado y en uso 1024. Máximo sin cambios (2147483647). Reversión: configurar mínimo en 0 y ejecutar RECONFIGURE. Sin reiniciar SQL Server ni modificar datos contables. El mínimo no reserva inmediatamente 1 GB ni garantiza por sí solo resolver lentitud. Documentación: https://learn.microsoft.com/en-us/sql/database-engine/configure-windows/server-memory-server-configuration-options
- Respuestas sobre contacto 375: (a) sí, las transferencias de 2024 con retención son honorarios; (b) Sergio necesita ver el detalle de transferencias sueltas antes de confirmar retiros; (c) manda el recibo formal. Los 250 kg + US$ 550 son únicamente referencia para comparar el sueldo con el negocio, no obligación salarial ni diferencia automática a socio.
- Detalle actualizado: [sergio-375-pagos-para-revisar-20261022.md](sergio-375-pagos-para-revisar-20261022.md). La reproducción literal con fechas normalizadas da 117 pagos candidatos a sueldo, 52 a socio y 37 sin contraparte por $8.475.209,51. Difiere de 113/58/38 del traspaso: no usar esos conteos como clasificación definitiva ni aplicar correcciones con este cruce por monto/fecha. Incluye retenciones y efectivo, además de transferencias. Falta cotejar comprobantes y correspondencia uno a uno. No se reclasificaron movimientos.

- Revisión de `Personal/Empleados.xlsx`, hoja `Pagos Sergio G`: P01/P02 confirmados por Sergio como sueldos; P03–P09 con evidencia salarial y diferencias de fecha/cuenta explicitadas en el detalle y su HTML. Cruce exacto insuficiente para pagos acumulados/parciales. Se detectaron diferencias de distribución diciembre-2011/enero-2012 y pago adicional en WC del 13/08/2012 por $8.000. No se modificaron Excel ni datos de WC.

- Sergio explicó que durante un período cobraba sueldos y los devolvía en efectivo a caja. Revisión personal + caja: ver `sergio-375-retornos-sueldo-20261022.md`. P12 directo; P10/P11 compatibles; P13 no cierra; P14 parcial $20.000; P15 banco receptor dice honorarios; P16 $70.000 receptor vs $140.000 emisor asignados al 375; P17 solo coincidencia parcial $200.000. S01–S03 respaldados como acreditaciones salariales. 19 retornos explícitos en caja por $328.503, sin aplicar ajustes ni duplicar socio. No hubo escrituras contables.

- Revisión Estudio Contable completada para el alcance 375: 105 PDF seleccionados, 15 planillas, 12 recibos del RAR2021, más 13 recibos de Personal para cotejo. Estado vigente en `sergio-375-pendientes-resumen-20261022.md` y HTML homónimo en backups. Hallazgo crítico: marzo–junio2024 netos exactos de recibos; P27+P28=$1.013.327=neto julio con devolución de Ganancias $63.326,76. No crear honorarios adicionales por esos pagos pese a hipótesis anterior. P16/P17/P30: diferencias emisor/receptor $70.000/$200.000/$160.000 (investigar; sin reasignación aplicada). P31/P32 banco: reembolsos; P33: honorarios. Diciembre2024 tiene recibo/pago $1.425.000 y falta remuneración en vista375. Sin escrituras contables; cuenta no cerrada.

## 5. Continuidad entre Claude y Codex

Sergio reiteró que todo el trabajo debe quedar registrado para que cualquiera de los dos agentes pueda continuarlo. La regla quedó explícita en `.specify/memory/agent-guidance.md`.

- **Estado vigente:** `sergio-375-pendientes-resumen-20261022.md` contiene pendientes para Sergio, investigación interna, hallazgos y conciliación documental, con fuentes. Los análisis anteriores se conservan como historia y remiten a ese estado.
- **Presentación para Sergio:** `backups/sergio-375-20261022/Sergio - pendientes y resumen.html`. Sergio prefiere informes legibles en navegador, no mostrar Markdown. Abrir con `Start-Process -FilePath` sobre la ruta Windows verificada. Para pegar en navegador usar `file:///C:/...` con espacios codificados; `/C:/...` no es una dirección válida para pegar.
- **Evidencia local:** índices/extracciones en `backups/sergio-375-20261022/extractos-personales/` y `backups/sergio-375-20261022/estudio-contable/`. Los originales siguen en las carpetas de Documents citadas en el informe; los PDF y las planillas son la evidencia, no la extracción textual. `backups/` es local y no se versiona.
- **Verificaciones del último tramo:** 105 PDF extraídos sin errores y con texto; referencias de fuentes del informe comprobadas como archivos existentes; informe HTML con tres tablas y estructura cerrada; apertura solicitada mediante el navegador predeterminado. No se hizo una inspección visual del HTML con herramientas de navegador.
- **Cambios efectivos:** reinicio de aplicación y mínimo de memoria SQL Server aplicado/verificado en 1024 MB. Lo demás fue lectura, análisis y documentación: no se corrigieron movimientos contables, no se guardaron cambios en Excel y no se cerró la cuenta 375.
- **Siguiente paso:** continuar con los pendientes del informe vigente; investigar P16/P17/P30 contra los comprobantes del emisor y destinatarios antes de reclasificar. Conservar la pausa del Condominio/Virginia y evitar duplicar sueldos, retenciones y retornos.
- **Git al registrar este avance:** documentación modificada/nueva en la carpeta compartida `specs/036-revision-sistematica-cuentas/`, todavía sin commit ni push en esta retoma. Claude puede leerla directamente en este mismo workspace. No confundirla con documentos ya subidos a main antes de esta sesión.

## 6. Retoma de Claude, 22/10/2026 por la tarde (solo documental)

- Se leyeron la guía, el avance y el resumen vigente; se preservaron los cambios de Codex sin commitear.
- **P16/P17/P30 resueltos documentalmente** con los extractos Galicia de Lucy:
  - P16 y P17 eran pagos en lote; $70.000 y $200.000 fueron para Lucy.
  - En P30, los Mov. Galicia 2198 ($250.000) y 2199 ($90.000) tienen los contactos 375/390 cruzados.
  - Las planillas Cuenta Sergio/Lucy ya tenían el reparto correcto.
- **Resueltos además:**
  - P15 y P37: cobro y devolución a caja el mismo día.
  - P29, P33 y P34: retiros por aportes del Condominio (Cuenta Cond LSC).
  - P32 y P35: devolución por aporte (Cuenta Sergio) + Condominio.
  - P36: débito de Allianz de mayo de 2026.
  - P18: probable ajuste del sueldo de agosto de 2023 (hoja Sueldo Sergio $330.000 contra recibo $300.000), a confirmar.
- **Siguen pendientes:** P31 ($485.400 del 10/09/2025, sin rastro en planillas), P10–P11, P13 y P14.
- **Sin escrituras:** WC, Access y planillas sin cambios. Las correcciones propuestas (dividir 267 y 683, cruzar 2198/2199, separar del 375 los pagos que no son sueldo, devolver P36 a Allianz) esperan la aprobación de Sergio. Detalle en `sergio-375-pendientes-resumen-20261022.md` (estado vigente, reescrito).
- **Informe para Sergio:** `backups/sergio-375-20261022/Sergio - pendientes y resumen (Claude).html`, abierto en el navegador.
- **Actualización 14:20:**
  - Respuestas de Sergio:
    - P18: manda el recibo.
    - P31: probable compensación.
    - Aprobó los puntos 3, 5 y 6; pidió explicación de los puntos 1, 2 y 4.
  - Aplicado:
    - Cruce de contactos 2198/2199 (`sergio_lucy_galicia_20241104_036.py`).
    - Devolución de Ganancias de julio de 2024 y redondeos (`sergio_sueldos_2024_ganancias_036.py`).
    - Saldo 375: $8.465.329,55.
  - Diciembre de 2024 no faltaba.
  - El punto 5 son 20 débitos de Allianz reasignados al 375 y la ficha de Allianz está cerrada: consultado, sin aplicar.
  - Detalle completo en la sección "Actualización 14:20" de `sergio-375-pendientes-resumen-20261022.md`.
  - Informe: `backups/sergio-375-20261022/Sergio - cuenta 375 respuestas (Claude).html`.
- **Actualización 14:35 (aplicado):**
  - Allianz de la Taos devuelto a 515 con asientos Particular S (regla de compras particulares **siempre**).
  - Cuenta de Sergio separada: 375 = empleado; **5670 = "Sergio Giamberardini (socio)"**, con 41 movimientos reasignados.
  - Ajustes de los pagos en lote con Lucy y del excedente de febrero de 2024.
  - P31 en la cuenta de socio.
  - Alerta operativa en pantalla (`AvisoCuentaContacto`).
  - 375 = −$2.105.297,52 (sueldo de septiembre de 2026 a pagar en octubre + historia 2011-2019 + P18).
  - Pendiente: la fila P31 en la planilla (Excel abierto) y P18.
  - Ver `sergio-375-pendientes-resumen-20261022.md`, sección 14:35.
