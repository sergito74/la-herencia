# Diseño: Inversiones (plazos fijos y FCI Fima) en Tesorería, Inicio y Flujo de caja

19/11/2026. Agentes 12 (diseño visual) y 08 (funcionalidad ERP), sobre el análisis contable de `specs/036-revision-sistematica-cuentas/analisis-inversiones-fci-plazo-fijo-20261119.md` (agentes 10 y 07). Mismo lenguaje que `auditoria-imputacion-20261118.md` y `auditoria-tesoreria-20261119.md`: tabla densa, KPI arriba, filtros con contadores (`Segmentos`), detalle en `SideDrawer`.

**Estado:** diseño para el **modelo C** (medio "Inversiones" con 3 subcuentas, capital como traspaso interno, diferencia como documento interno "Rendimiento de inversión" al rubro "Resultados financieros"). Sergio todavía no lo aprobó. Cada sección termina con **"Si cambia el modelo"**.

Reglas aplicadas: formato argentino (`$ 1.234.567,89`, fechas `dd/mm/aaaa`, % con coma), nada de ids, comprobantes internos, usuarios ni "sistema" en pantalla; rojo solo para alertas (excepción, diferencia de saldo); verde solo para "cerrado/al centavo"; el rendimiento positivo va en color de texto normal, no verde. Sección "Textos que sobran" del agente 12: en las filas va solo el estado corto; motivo, par y detalle van al panel.

---

## 1. Pestaña "Inversiones" de Tesorería

Ubicación: nueva pestaña al mismo nivel que Banco Nación, Galicia y Mercado Libre en `finanzas/tesoreria`. Mantiene el `PageHeader` de Tesorería; la pestaña tiene su propio cuerpo.

### 1.1 Boceto (escritorio, ≥1280 px)

```
Tesorería                                                [Revisar ahora]
[Banco Nación] [Galicia] [Mercado Libre] [Inversiones •2]
-------------------------------------------------------------------------
┌─────────────────┐┌─────────────────┐┌─────────────────┐┌─────────────────┐
│ Invertido hoy   ││ Rendimiento 2026││ Próximo venc.   ││ Para revisar    │
│ $ 78.512.096,88 ││ $ 6.440.308,88  ││ —               ││ 4               │
│ Fima al 30/09   ││ PF $ 107.397,26 ││ sin plazos fijos││ (rojo si > 0)   │
│                 ││ Fima $ 6.332.911││ abiertos        ││ Ver ›           │
└─────────────────┘└─────────────────┘└─────────────────┘└─────────────────┘

Ver: [Cartera vigente] [Historial 48] [Rendimiento] [Para revisar 4] [Control de saldos]

── Cartera vigente ──────────────────────────────────────────────────────
 Subcuenta          Desde       Vence       Capital / saldo   Tasa      Esperado
 FCI Fima Galicia   30/09/2026  —           $ 78.512.096,88   —         —
   920.123,45 cuotapartes a $ 85,37 · movimientos sin valuar: 6  ›
 Plazo fijo BNA     (sin plazos fijos abiertos)
 Plazo fijo Galicia (sin plazos fijos abiertos)
 ─────────────────────────────────────────────────────────────────────
 Total invertido                                $ 78.512.096,88
```

- KPI con `KpiCard`. "Para revisar" usa tono de alerta solo si es > 0; con 0 muestra "Todo al día" en gris.
- "Próximo vencimiento" muestra fecha + banco + importe del plazo fijo abierto que vence primero; sin plazos fijos, "—".
- "Invertido hoy" aclara la fecha del último saldo oficial del Fima ("Fima al 30/09"); si hay movimientos posteriores, el número es saldo oficial + suscripciones − rescates posteriores y la leyenda dice "estimado".
- Fila del Fima: segunda línea gris con cuotapartes y valor; "movimientos sin valuar: 6" abre el panel del mes en curso.

### 1.2 Historial

```
Ver: Historial   Tipo: [Todos 48] [Plazo fijo 19] [Fima 31]   [RangoFechas]
 Subcuenta          Período                   Capital / saldo inicial  Rendimiento    Tasa      Estado
 FCI Fima Galicia   Septiembre 2026           $ 70.114.000,00          $ 812.345,67   1,16%     Cerrado
 Plazo fijo BNA     18/12/2025 → 19/01/2026   $ 5.000.000,00           $ 107.397,26   2,15% 32 d Cerrado
 Plazo fijo BNA     03/11/2025 → 03/12/2025   $ 9.000.000,00           $ 281.095,89   3,12% 30 d Cerrado
 Plazo fijo Galicia 12/09/2023 → ?            $ 4.500.000,00           —              —         Para revisar
```

- `DataTable` con `onRowClick` → panel lateral. Columna Estado con `StatusBadge`: "Cerrado" (neutro), "Para revisar" (rojo), "Fuera de alcance" (gris), "Esperando extracto" (ámbar).
- Orden por fecha descendente. Totales al pie del filtro activo.

### 1.3 Rendimiento

```
Ver: Rendimiento   Agrupar: [Por año] [Por mes]
   7 M ┤                                              ▇▇
   6 M ┤                                         ▇▇   ▇▇
   ... ┤ barras apiladas: PF BNA / PF Galicia / Fima
     0 ┼──▁───▂───▁───▁───────▃───▅───▇───▇──
        2018 2019 2020 2021 2022 2023 2024 2025 2026
 Año    PF BNA        PF Galicia     FCI Fima        Total
 2026   107.397,26    —              6.332.911,62    6.440.308,88   (Fima hasta 30/09)
 2025   281.095,89    —              5.842.119,58    6.123.215,47
 2024   —             a revisar      2.837.065,68    2.837.065,68
 ...
```

- Gráfico de barras apiladas simple (3 series, paleta neutra; nada de rojo). Por mes: últimos 12 meses.
- 2024 Galicia muestra "a revisar" (no un número) hasta que se resuelva el par 4,5 M / 9,26 M. Debe coincidir con la §4 del análisis.
- Celda clic → Historial filtrado a ese año/subcuenta.

### 1.4 Para revisar (excepciones)

```
Ver: Para revisar   [Todas 4] [Falta un lado 2] [Falta extracto 2] [Diferencia de saldo 0] [Fuera de alcance 0]
 Fecha       Subcuenta          Qué pasa                                  Importe          Acción
 12/09/2023  Plazo fijo Galicia Constitución sin acreditación             $ 4.500.000,00   [Emparejar]
 14/08/2024  Plazo fijo Galicia Acreditación sin constitución             $ 9.257.546,87   [Emparejar]
 02/06/2016  Plazo fijo BNA     Débito sin acreditación (posible duplicado) $ 200.000,00   [Resolver ▾]
 Oct. 2026   FCI Fima Galicia   Falta el extracto de fin de mes           rescates $ 12,6 M [Adjuntar extracto]
```

Los textos de "Qué pasa" son cortos y fijos (catálogo de 6: constitución sin acreditación, acreditación sin constitución, abierta hace más de 400 días, falta el extracto de fin de mes, rendimiento negativo, saldo distinto del extracto). Nada de detalle técnico en la fila.

### 1.5 Panel lateral (`SideDrawer`)

**Plazo fijo cerrado**

```
┌ Plazo fijo BNA · 18/12/2025 → 19/01/2026 ───────────── [×]
│ Cerrado
│
│ Constitución   18/12/2025  Banco Nación   − $ 5.000.000,00  ›
│ Acreditación   19/01/2026  Banco Nación   + $ 5.107.397,26  ›
│ ───────────────────────────────────────────────
│ Capital (traspaso a Inversiones)   $ 5.000.000,00
│ Interés (Resultados financieros)   $   107.397,26
│ Plazo 32 días · tasa del período 2,15% · TNA 24,50%
│
│ Comprobante del banco: [ver PDF]   (si está adjunto)
│
│ [Deshacer emparejamiento]                      (texto, no botón primario)
└────────────────────────────────────────────────────────
```

`›` abre el movimiento en su pestaña bancaria. El número de comprobante del banco no se muestra (se usa solo para aparear).

**Mes de Fima**

```
┌ FCI Fima Galicia · Septiembre 2026 ──────────────────── [×]
│ Cerrado · saldo igual al extracto
│
│ Saldo inicial (31/08)        $ 70.114.000,00
│ + Suscripciones (3)          $ 15.000.000,00  ›
│ − Rescates (8)               $  7.414.248,79  ›
│ Saldo final (30/09, extracto) $ 78.512.096,88
│ ───────────────────────────────────────────────
│ Rendimiento del mes          $    812.345,67   (1,16%)
│ Cuotaparte  $ 84,40 → $ 85,37
│
│ Extracto: [ver PDF]
└────────────────────────────────────────────────────────
```

"(3)" y "(8)" despliegan la lista de movimientos (fecha, importe) dentro del panel.

**Excepción: emparejar a mano** (pocos clics)

```
┌ Constitución sin acreditación ───────────────────────── [×]
│ 12/09/2023 · Plazo fijo Galicia · − $ 4.500.000,00
│
│ Elegí la acreditación que le corresponde:
│ ( ) 14/08/2024  + $ 9.257.546,87   337 días · sugerida
│ ( ) 05/10/2023  + $ 4.353.983,56   ya emparejada (deshabilitada)
│
│ Vista previa
│ Capital $ 4.500.000,00 · Interés $ 4.757.546,87 · 337 días
│ ⚠ Más de 30 días: probable renovación con capitalización.
│   Adjuntá la constancia si la tenés.  [Adjuntar]
│
│ [Confirmar par]   [Marcar fuera de alcance]
└────────────────────────────────────────────────────────
```

- 1 clic abre, 1 clic elige (la sugerida ya viene marcada), 1 clic confirma = 3 clics.
- **Confirmar** una propuesta ambigua de la regla automática: mismo panel, con la candidata preseleccionada y botones [Confirmar] / [Rechazar].
- **Fuera de alcance**: abre un campo "Motivo" obligatorio (ej. "Duplicado heredado de 2016") y [Guardar]. La fila queda visible con badge gris en el filtro "Fuera de alcance"; se puede deshacer.
- **Falta el extracto**: [Adjuntar extracto] sube el PDF de Galicia; el sistema lee la posición y cierra el mes. Nunca se tipea el saldo.

### 1.6 Control de saldos

```
Ver: Control de saldos
 Subcuenta           Mes         Saldo sistema     Saldo extracto     Diferencia
 FCI Fima Galicia    Sep. 2026   $ 78.512.096,88   $ 78.512.096,88    $ 0,00 ✓
 FCI Fima Galicia    Oct. 2026   $ 66.000.000,00   —                  esperando extracto
 Plazo fijo BNA      hoy         $ 0,00            $ 0,00             $ 0,00 ✓
```

Diferencia ≠ $ 0,00 (aunque sea un centavo) → rojo y genera excepción. Sin tolerancias.

### 1.7 Estados vacíos y carga
- `EmptyState` en cada vista ("No hay plazos fijos abiertos", "Todo revisado").
- `Callout` informativo solo si hay meses de Fima esperando extracto: "Faltan los extractos de octubre y noviembre del Fima. [Adjuntar]".
- Móvil: KPI en 2×2, tablas pasan a tarjetas (subcuenta + período arriba, importe a la derecha, estado abajo).

**Si cambia el modelo:** con la alternativa B (sin medio Inversiones) desaparecen "Cartera vigente" y "Control de saldos" como subcuentas: la pestaña queda como un reporte (Historial + Rendimiento + Para revisar) y "Invertido hoy" pasa a ser un dato leído del extracto, no un saldo del sistema. Con la A, no hay pestaña: solo un informe de rendimiento fuera de Tesorería.

---

## 2. El movimiento de inversión en Banco Nación / Galicia

En la fila: solo una etiqueta corta en la columna Conciliación.

```
 Fecha       Concepto                 Importe            Conciliación
 18/12/2025  Constitución plazo fijo  − $ 5.000.000,00   Inversión
 19/01/2026  Acreditación plazo fijo  + $ 5.107.397,26   Inversión
 03/09/2026  Rescate Fima             + $ 2.000.000,00   Inversión
 12/09/2023  Constitución plazo fijo  − $ 4.500.000,00   Inversión · revisar   (rojo)
```

- No se escribe "Conciliado", ni "Traspaso interno", ni el número de comprobante, ni quién lo concilió.
- Filtro existente "Pendientes de conciliar": los "Inversión · revisar" cuentan como pendientes.
- Panel "Ver / corregir" del movimiento: bloque "Inversión" con subcuenta, el movimiento par (fecha + importe, enlace), el desglose capital / interés y un enlace "Ver en Inversiones ›" que abre la pestaña con el panel del par o del mes.
- Acreditación con interés: el panel muestra dos tramos ("$ 5.000.000,00 traspaso a Inversiones", "$ 107.397,26 interés"), nunca dos filas.

**Si cambia el modelo:** con B la etiqueta sigue siendo "Inversión" y el panel muestra el par y el interés calculado, sin subcuenta. Con A la fila diría "Conciliado" como hoy (no recomendado).

---

## 3. Inicio y Flujo de caja / resultados

### 3.1 Tarjeta en Inicio (`app/page.tsx`)

```
┌ Inversiones ───────────────────────┐
│ $ 78.512.096,88  invertido          │
│ Próximo vencimiento: —              │
│ 4 para revisar                (rojo)│
│                       Ver detalle › │
└────────────────────────────────────┘
```
Mismo tamaño y estilo que las tarjetas actuales de Inicio; enlace a `/finanzas/tesoreria?medio=inversiones`. Con 0 para revisar, esa línea no aparece.

### 3.2 Flujo de caja

```
 Rubro                              Ene   Feb   ...   Sep          Total 2026
 Ingresos operativos ...
 ...
 Resultados financieros                               $ 812.345,67  $ 6.440.308,88  ›
   Intereses plazo fijo                               —             $   107.397,26
   Rendimiento FCI                                    $ 812.345,67  $ 6.332.911,62
   Intereses y comisiones bancarias (egreso)          ...
 Movimientos entre cuentas propias   (ya no incluye el interés)
```
- Fila agrupadora debajo del neto operativo, colapsable. Clic → `SideDrawer` con los pares/meses del período y enlace a Inversiones.
- No aparece en Resultado de cultivo. En un futuro estado de resultados de la empresa, va en Administración general.

**Si cambia el modelo:** la fila de flujo de caja existe en las tres alternativas (el análisis lo exige para que el interés no se pierda); con A habría que separar el interés en la clasificación del flujo sin documento.

---

## 4. Flujos de usuario

### 4.1 Plazo fijo que vence (automático)
1. Entra el extracto de Banco Nación (o corre la revisión diaria).
2. El sistema encuentra la constitución y la acreditación con el mismo comprobante, crea el traspaso por el capital y el documento "Rendimiento de inversión" por el interés.
3. En Banco Nación ambas filas muestran "Inversión"; el plazo fijo pasa de Cartera vigente a Historial "Cerrado"; el KPI de rendimiento del año suma.
4. Sergio no hace nada. Si quiere, abre el panel y ve el par y la tasa.
5. Galicia (sin comprobante): igual, salvo que si hay más de una acreditación posible o tasa rara, queda "Para revisar" con la propuesta preseleccionada → 1 clic en [Confirmar].

### 4.2 Mes de Fima (automático al leer el extracto)
1. Durante el mes, cada suscripción/rescate se marca "Inversión" en Galicia en cuanto entra.
2. El mes aparece en Historial como "Esperando extracto" y en Control de saldos.
3. Se lee el PDF del extracto de Galicia: el sistema toma saldo, cuotapartes y valor, calcula el rendimiento y crea el documento del mes.
4. Si saldo del sistema = extracto al centavo → "Cerrado ✓". Si da negativo o hay diferencia → "Para revisar" (no bloquea).

### 4.3 Excepción
1. KPI "Para revisar 4" en rojo (también en Inicio) → clic.
2. Vista "Para revisar" filtrada; clic en la fila → panel.
3. Según el caso: elegir el par sugerido y [Confirmar par]; o [Marcar fuera de alcance] + motivo; o [Adjuntar extracto].
4. La fila desaparece del contador y pasa a Historial con su estado. Todo se puede deshacer desde el panel.

---

## 5. Lista implementable (priorizada)

| # | Qué | Archivos | Esfuerzo |
|---|---|---|---|
| 1 | Backend: tabla de movimientos de inversión, medio "inversiones" en `MEDIOS_SOPORTADOS`, tipo de documento interno, rubro "Resultados financieros" | `backend/.../tesoreria/*`, `traspasos_internos_tesoreria`, migración SQL en WC | Alto (requiere aprobación del modelo) |
| 2 | Reglas automáticas BNA / Galicia PF / Fima + "Revisar ahora", reemplazo de los 37 sin documento | servicio nuevo `tesoreria/inversiones.py`, hook en el arranque/diario/post-extracto (como Ley 25.413) | Alto |
| 3 | Endpoints de lectura (abajo) | router de tesorería | Medio |
| 4 | Pestaña Inversiones: KPI, Segmentos, Cartera, Historial, Para revisar | `frontend/src/components/tesoreria/InversionesTab.tsx` (+ `InversionesTabla.tsx`), alta de la pestaña en `app/finanzas/tesoreria/page.tsx` | Medio |
| 5 | Paneles: plazo fijo, mes Fima, excepción (emparejar/confirmar/fuera de alcance/adjuntar) | `components/tesoreria/InversionPanel.tsx` sobre `SideDrawer` | Medio |
| 6 | Etiqueta "Inversión" y bloque en el panel del movimiento bancario | componentes de fila y "Ver / corregir" de `components/tesoreria/*` | Bajo |
| 7 | Rendimiento (gráfico + tabla) y Control de saldos | `InversionesRendimiento.tsx` | Bajo-medio |
| 8 | Tarjeta en Inicio | `frontend/src/app/page.tsx` | Bajo |
| 9 | Fila "Resultados financieros" en Flujo de caja y quitar el interés de "entre cuentas propias" | `flujo_caja/clasificacion.py`, pantalla de flujo de caja | Medio |
| 10 | Lectura de la posición Fima desde el PDF (deja de usarse el JSON a mano) | lector de extractos Galicia | Medio |

Orden sugerido para mostrar valor rápido sin escribir en base: 3 (lectura sobre los datos actuales) → 4, 7, 8 en solo lectura; luego, con el modelo aprobado, 1, 2, 5, 6, 9, 10.

### Endpoints de lectura (se reusan los de la §7, con ajustes)
- `GET /tesoreria/inversiones/resumen` (**nuevo**, alimenta KPI y tarjeta de Inicio): invertido hoy, fecha del último saldo oficial, rendimiento del año por subcuenta, próximo vencimiento, cantidad para revisar.
- `GET /tesoreria/inversiones/cartera`
- `GET /tesoreria/inversiones/historial?tipo=pf|fci&desde&hasta` (cada ítem con sus movimientos par/lista para el panel, y `estado`).
- `GET /tesoreria/inversiones/rendimientos?agrupar=anio|mes`
- `GET /tesoreria/inversiones/excepciones` (tipo del catálogo de 6, candidatos con la sugerida marcada, vista previa del interés).
- `GET /tesoreria/inversiones/control-saldos`
- Agregar a la respuesta de movimientos bancarios un campo `inversion` (subcuenta, par, capital, interés, estado) para la etiqueta y el panel, sin endpoint aparte.
- Escritura (después de aprobar): los de la §7 más `POST .../extracto-fima` (adjuntar PDF).

Textos de interfaz: todo lo que vuelva del backend como tipo o estado se traduce en el front a los textos de este documento; ningún código llega a pantalla.
