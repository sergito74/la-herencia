# Implementation Plan: Imputación progresiva y tamizado de facturas a cultivo/campaña (049 + 050)

**Branch**: `050-tamizado-imputacion-cultivos` (se trabaja en `main`, push autorizado) | **Date**: 2026-11-14

**Spec**: [spec.md](spec.md) + [../049-imputacion-automatica-total/spec.md](../049-imputacion-automatica-total/spec.md)

**Inputs**: [tabla-rubros-destino.md](tabla-rubros-destino.md) (cerrada 14/11) · [preguntas-20261114.md](preguntas-20261114.md) (50 respuestas)

## Summary

Cada renglón de una factura **nueva** pasa por un **tamiz por rubro** que lo manda a uno de estos destinos:

- **A cultivo (stock)**: insumos.
- **A cultivo (una vez)**: labores, seguros, comercialización, etc.
- **Depende**.
- **Ganadería**.
- **Financiero**.
- **Estructura**.
- **No se imputa**.

Los insumos siguen la **imputación progresiva por renglón**:
- El renglón entra entero "en stock".
- Cada orden ejecutada le descuenta un uso, primero lo que entró antes, con su cultivo/campaña.
- El saldo queda en stock.

Los remitos manejan la cantidad y las facturas el precio. El vínculo remito↔factura se arma solo.

Lo ya imputado no se toca.

**Enfoque técnico**: reutilizar lo que ya existe (017/048):

- el FIFO de `remitos.stock_datos.calcular_stock`;
- `imputacion.motor.calcular_propuesta_insumo`, que ya calcula usos + stock por renglón de factura;
- las corridas versionadas en `ImputacionPropuestas`;
- los disparadores de recálculo en órdenes y remitos.

Lo nuevo se reduce a cinco piezas:

1. Las tablas de tamiz (rubro → destino/parte), la regla por producto y el alcance.
2. El vínculo automático remito↔factura y una capa "factura sin remito".
3. El motor de tamiz con su orden de prioridad.
4. El resultado del cultivo sin doble conteo para los renglones en alcance.
5. La pantalla "Para revisar" con contador, la sugerencia en la carga de compra y el informe por parte.

## Technical Context

- **Language/Version**: Python 3.13 (backend FastAPI) y TypeScript con Next.js (frontend).
- **Primary Dependencies**: FastAPI, pyodbc (`src.db.connection`), Next.js, Tailwind, TanStack Query.
- **Storage**: SQL Server `WC`. Hay tablas nuevas, y antes de crearlas se hace un backup verificado (Principio II).
- **Testing**: pytest con mocks de `fetch_all`/`execute_write_transaction` (patrón de `tests/test_imputacion_*`), más verificación de lectura contra WC.
- **Target Platform**: PC de Sergio, con el lanzador `LaHerencia.ps1`. Escucha solo en 127.0.0.1.
- **Project Type**: aplicación web (backend + frontend).
- **Performance Goals**:
  - El tamiz de una factura al guardarla tarda menos de 2 s.
  - La pasada diaria completa tarda menos de 10 min.
- **Constraints**:
  - Sin tolerancias: se concilia al centavo.
  - Los renglones fuera de alcance no cambian.
  - Lo de San Justo sigue bloqueado.
  - No se muestran identificadores internos en pantalla.
- **Scale/Scope**:
  - Unos 1.900 renglones por año.
  - 392 insumos sin producto.
  - 48 rubros en uso.
  - Unos 200 productos con stock.

## Constitution Check

| Principio | Cumple | Nota |
|---|---|---|
| I. WC es el sistema de registro | ✅ | Todo lee y escribe en WC; nunca en LaHerencia. |
| II. Protección de datos | ✅ | Backup verificado antes de crear tablas y antes del primer barrido de alcance. Tests con mocks. Sin registros de prueba en WC. |
| III. Procesos, no tablas | ✅ | El usuario ve "Para revisar", la sugerencia en la compra y el informe por cultivo. |
| IV. Trazabilidad | ✅ | Cada fracción conserva renglón, orden, remito, motivo y corrida, con historial por corrida. |
| V. Contrato primero | ✅ | [contracts/api.md](contracts/api.md) se escribe antes de la UI. |
| VI. Especialistas | ✅ | 10 agentes aportaron las 50 preguntas; las decisiones de dominio quedaron registradas. |
| VII. Simplicidad | ✅ | Se reutilizan motor, FIFO y corridas; no hay motor nuevo de stock. |
| VIII. Stack | ✅ | Python, SQL Server, Next.js, TS, Tailwind, TanStack Query. |

**Gate**: pasa. Después del diseño se re-evaluó y sigue pasando (ver [research.md](research.md) R-07 sobre el doble conteo heredado).

## Project Structure

### Documentation (this feature)

```text
specs/050-tamizado-imputacion-cultivos/
├── spec.md · preguntas-20261114.md · tabla-rubros-destino.md(.html)
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/api.md
└── tasks.md            # /speckit-tasks
```

### Source Code

```text
backend/
├── scripts/
│   ├── crear_tablas_tamiz_050.py        # DDL + carga de la tabla rubro→destino (idempotente)
│   ├── activar_alcance_050.py           # fija el corte y marca renglones viejos sin imputar con stock
│   └── imputacion_diaria_050.py         # pasada diaria (Programador de tareas, como peajes)
├── src/features/imputacion/
│   ├── tamiz.py                         # NUEVO: clasificación por renglón con prioridad fija
│   ├── tamiz_repository.py              # NUEVO: reglas rubro/producto, alcance, cola de revisión
│   ├── producto_sugerido.py             # NUEVO: descripción → producto del catálogo
│   ├── motor.py                         # + capa factura-sin-remito, + destino por parte, silobolsa por uso
│   ├── repository.py                    # + filtros de alcance
│   └── router.py                        # + endpoints de tamiz / revisión / contador
├── src/features/remitos/
│   ├── vinculo_auto.py                  # NUEVO: remito↔factura automático (parcial incluido)
│   └── stock_datos.py                   # + capas "F{idDetalleCompra}" para facturas sin remito en alcance
├── src/features/compras/                # al guardar → tamiz.tamizar_compra(id)
├── src/features/ordenes/repository.py   # al ejecutar → recalcula también renglones en alcance sin corrida
├── src/features/resultado_cultivo/costos.py  # sin doble conteo + agrupado por parte
└── tests/test_tamiz_050*.py, test_vinculo_auto_050.py, test_costos_alcance_050.py

frontend/src/app/
├── imputacion/revisar/page.tsx          # NUEVO "Para revisar"
├── compras/[id]/editar/…                # etiqueta + sugerencia por renglón
├── resultado-cultivo/…                  # informe por parte $/ha y US$/ha
└── (layout) contador en el menú
```

**Structure Decision**: la estructura web existente. Las piezas nuevas viven dentro de los módulos `imputacion` y `remitos`, que ya manejan este dominio.

## Fases de entrega (orden de implementación)

1. **Base**:
   - backup;
   - tablas de [data-model.md](data-model.md);
   - carga de la tabla rubro→destino;
   - fecha de corte del alcance.
2. **Tamiz** (Historias 050-2/3): `tamiz.py` con la prioridad manual > orden > producto > rubro > lista. Por ahora solo guarda la clasificación; todavía no cambia el resultado.
3. **Vínculo remito↔factura + capa factura sin remito** (049-Historia 2, FR-013).
4. **Imputación progresiva**:
   - el disparador al ejecutar una orden incluye los renglones en alcance;
   - pasada diaria;
   - fracciones de una sola vez (Origen `Directo`) para los renglones "a cultivo (una vez)".
5. **Resultado sin doble conteo + informe de impacto** (049 FR-012):
   - antes de activar, se genera el Excel antes/después por cultivo/campaña y se muestra a Sergio;
   - recién después se activa.
6. **Producto sugerido** y aprendizaje por producto.
7. **UI**: "Para revisar", contador, sugerencia en la compra e informe por parte.
8. **Control de cierre** comprado = aplicado + stock + bajas (049 Historia 5).

## Complexity Tracking

No hay violaciones que justificar.
