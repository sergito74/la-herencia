# Research: Traspasos internos de Tesorería

## 1. ¿Cómo modelar el vínculo entre dos movimientos, con soporte de deshacer, sin UPDATE/DELETE?

**Decisión**: tabla nueva insert-only `dbo.TraspasosInternosTesoreria`, donde cada fila es un **evento** (`Vincular` o `Deshacer`), no un estado mutable — mismo patrón ya usado en `ReasignacionesContacto` (022, "la fila vigente es la de mayor Id"):

```
IdEvento        (PK, identity)
MedioA, IdMovimientoA
MedioB, IdMovimientoB
Accion          ('Vincular' | 'Deshacer')
Usuario
Fecha           (default getdate())
```

Un vínculo está **activo** para un par `(MedioA/IdMovimientoA, MedioB/IdMovimientoB)` si su evento `Vincular` más reciente no tiene un evento `Deshacer` posterior para el mismo par. Deshacer (FR-010) es simplemente otra fila con `Accion='Deshacer'` — nunca se borra ni actualiza la fila original, preservando el historial completo (FR-013) sin necesitar una columna de estado que se pueda desincronizar.

**Alternativas consideradas**:
- *Una columna `Activo bit` mutable con `UPDATE` al deshacer* — rechazado: rompe el patrón insert-only ya establecido en 021/022/023, y complica la auditoría (perdería el "quién deshizo y cuándo" si no se agrega una tabla de historial aparte de todos modos).
- *Guardar el vínculo directamente en `ConciliacionesTesoreria` (023) con un `IdContacto` nulo* — rechazado: mezclaría dos conceptos con reglas distintas (023 tiene importe parcial/repartible, esto no tiene importe propio en absoluto — es un vínculo binario completo entre dos movimientos), y `ConciliacionesTesoreria.IdContacto` es `NOT NULL` por diseño (023, FR-005).

## 2. ¿Cómo determinar si un movimiento ya está "resuelto" (para el gate simétrico de FR-006)?

**Decisión**: una función central `esta_resuelto(medio, id_movimiento) -> str | None` en el nuevo módulo, que consulta en este orden — igual al orden de prioridad usado en el listado de Tesorería (023):
1. `ya_reconocido` (origen automático habitual — reusa `conciliacion_tesoreria.repository._contacto_reconocido_por_origen_automatico`, ya existente).
2. `conciliado` / `parcialmente_conciliado` (023 — reusa `conciliacion_tesoreria.repository.calcular_estado`).
3. `vinculado` (024 — el vínculo activo de este mismo módulo, sección 1).

Si cualquiera de estas tres devuelve algo distinto de "sin resolver", el movimiento no admite un vínculo nuevo (ni como iniciador ni como contraparte — Clarifications 2026-09-28, validación simétrica). Esta misma función se reutiliza para exponer el 5.º estado del listado de Tesorería (`traspaso_interno`), sumado a los 4 que ya expone 023.

**Alternativas consideradas**:
- *Duplicar la lógica de "ya reconocido"/"conciliado" dentro de este módulo nuevo* — rechazado: 023 ya la resuelve correctamente por medio (incluidas las particularidades de `valores-propios`/`valores-recibidos`, sin columna de contacto propia); duplicarla arriesga que diverja con el tiempo (Principio VII).

## 3. ¿Cómo sugerir automáticamente la contraparte (FR-005)?

**Decisión**: búsqueda por ventana de fecha ±5 días (mismo criterio ya validado en 023) con tolerancia de importe exacta o muy cercana (±$1, mismo criterio que 023/tarjetas), **sin exigir coincidencia de signo** entre medios (cada tabla de origen tiene su propia convención de Débito/Crédito, ya inconsistente entre sí — ver `tesoreria/repository.py`). Devuelve todos los candidatos dentro de esa ventana en los otros 5 medios cubiertos, ordenados por cercanía de fecha e importe — el usuario elige, nunca se auto-aplica (mismo principio que "Referencia de origen" y que el resto de las heurísticas de este sistema).

**Verificado contra datos reales** (`WC`, 2026-09-28): el caso conocido (ML `IdMovimiento=25`, "Ingreso de dinero Cuenta Banco de Galicia", $17.595,82, 2024-10-10) tiene una contraparte de **importe idéntico y misma fecha exacta** en Galicia (`IdMovimiento=2151`, "Debito Debin Preautorizado", $17.595,82, 2024-10-10) — confirma que el patrón real es lo bastante preciso (mismo día, mismo centavo) como para que una ventana ajustada (±5 días, ±$1) alcance sin necesidad de relajarla, y que SC-002 (90% de aciertos automáticos sobre el patrón conocido) es alcanzable con este criterio.

**Alternativas consideradas**:
- *Ventana ±10 días / tolerancia 2%* — descartada tras confirmar el match exacto: una ventana más ancha solo agregaría ruido (más candidatas irrelevantes por revisar) sin aportar nada, dado que el patrón real ya calza exacto.

## 4. ¿Qué endpoints necesita el backend?

**Decisión**: nuevo router `traspasos_internos_tesoreria`, mismo patrón que 023:
- `GET /api/tesoreria/{medio}/movimientos/{id}/traspaso-interno` — estado (vinculado o no, con el detalle de la contraparte si existe) + candidatas sugeridas (si no está vinculado).
- `POST /api/tesoreria/{medio}/movimientos/{id}/traspaso-interno` — aplica el vínculo con `{medioB, idMovimientoB}`.
- `DELETE /api/tesoreria/{medio}/movimientos/{id}/traspaso-interno` — deshace el vínculo activo (si existe).

**Alternativas consideradas**:
- *Reusar el mismo endpoint de 023 con un modo distinto* — rechazado: los contratos son semánticamente distintos (uno recibe `idContacto`+`importe`, el otro `medioB`+`idMovimientoB`, sin importe) — mezclarlos complica el contrato sin necesidad (Principio VII).

## 5. Integración con el listado de Tesorería (`estadoConciliacion`)

**Decisión**: el campo ya agregado en 023 (`estadoConciliacion` en cada ítem de `GET /api/tesoreria/{medio}/movimientos`) se extiende con el 5.º valor posible `traspaso_interno`, calculado en el mismo lugar (`tesoreria/router.py`) donde hoy se llama a `conciliacion_tesoreria.calcular_estado` por fila — se reemplaza esa llamada por `esta_resuelto` (sección 2), que ya encapsula los 5 estados en un solo lugar.

**Alternativas consideradas**: ninguna — es la continuación directa del mecanismo que 023 ya dejó preparado para esto (research.md de 023, sección 5, ya anticipaba "un 5.º estado" implícitamente al no cerrar el enum).
