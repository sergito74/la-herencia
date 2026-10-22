# Avance conciliaciones — 22/10/2026 (traspaso a Codex)

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
