# Quickstart: validación de extremo a extremo

Guía para comprobar que la funcionalidad cumple el [spec](spec.md). Contrato en [contracts/tarjetas-cuenta-api.md](contracts/tarjetas-cuenta-api.md); tablas y ramas en [data-model.md](data-model.md).

## Requisitos previos

- Backend y frontend instalados (`backend/.venv`, `frontend/node_modules`), base `WC` accesible.
- Rol con permiso de escritura para los pasos 7 y 8.
- Hacer el backup verificado de `WC` antes de los pasos 1 y 2 (lo hacen los propios scripts).

## 1. Instantánea previa y migración (solo `WC`)

```text
cd backend
python -m scripts.vista_tarjeta_cuenta_corriente --verificar     # no escribe: muestra qué haría
python -m scripts.vista_tarjeta_cuenta_corriente --ensayo        # todo dentro de una transacción con rollback: no deja cambios
python -m scripts.vista_tarjeta_cuenta_corriente                 # backup, tablas, ramas, instantánea previa
```

Esperado: backup verificado; `TarjetasContacto` con 5 filas; vista ampliada con las cuatro ramas; instantánea previa guardada antes de ampliar (saldo por contacto y totales mensuales del flujo de caja de 2024-01 a 2026-09). Es idempotente: una segunda corrida no cambia nada. Antes de la corrida real deben estar escritas las pruebas de las invariantes (tareas T027 y T028).

## 2. Preparar los datos de AgroNacion

```text
python -m scripts.preparar_tarjetas_cuenta_034 --verificar
python -m scripts.preparar_tarjetas_cuenta_034
```

Esperado: contacto "AgroNacion (administración anterior)" creado y 21 pagos de 2010 a 2012 ($23.575,00) reasignados a él; ninguna otra reasignación.

## 3. Comparación antes/después (SC-002, SC-008)

```text
python -m scripts.vista_tarjeta_cuenta_corriente --comparar
```

Esperado:
- Ningún cambio de saldo en contactos que no son tarjetas, salvo UATRE (+$17.185,82).
- Las cinco tarjetas con saldo coherente con su pendiente neto (diferencia menor a $1), una vez cruzada la devolución de AgroNacion (paso 7) y resuelto el pago de Mastercard BNA (tarea T053).
- El total general cambia en la deuda vigente incorporada (hoy $58.336.654,56 menos), las devoluciones cruzadas ($966.654,20 menos) y el pago de UATRE (+$17.185,82), y en nada más.
- Los totales mensuales del flujo de caja son idénticos a la instantánea.

## 4. Cuentas de las tarjetas (historia 1)

1. Abrir `Finanzas > Tarjetas`: se ven las cinco tarjetas con su saldo y el total.
2. Entrar a `Cuenta corriente` de AgroNacion y medir el tiempo de carga con la historia completa (objetivo: menos de 3 segundos); luego a la de Visa Galicia: consumos en su fecha, cargos en la fecha de cierre, pagos y saldo cronológico.
3. Filtrar un período: el saldo inicial refleja todo lo anterior; exportar y comprobar que el archivo repite filas y saldos.
4. Cambiar a "por resumen": el total de cada resumen coincide con el del módulo de tarjetas.
5. En AgroNacion: los resúmenes 571 a 578 no aparecen como deuda; el saldo final es $0 (después del cruce del paso 7) y la cuenta muestra el bloque de apertura de la administración anterior con enlace a esa cuenta.

Verificación por API: `GET /api/tarjetas-cuenta/resumen` y `GET /api/tarjetas-cuenta/4`.

## 5. Proveedores sin duplicación (historia 2 y FR-018)

```text
python -m pytest tests/test_vista_cuenta_tarjetas.py -q
```

Esperado: las invariantes de solo lectura pasan: consumos de tarjeta = vinculados + resto acreditado + consumos sin proveedor; ningún pago de resumen está en una cuenta de proveedor; las ramas nuevas no agregan filas a contactos que no son tarjetas, salvo UATRE.

## 6. Control de integridad (historia 3)

1. Abrir `Finanzas > Tarjetas > Control`.
2. Esperado con los datos ya preparados (después de reasignar los 21 pagos de la administración anterior): el débito 18093 de AgroNacion y el pago de Mastercard BNA sin resumen (b), la devolución sin cruzar (e), el pago con origen "Crédito banco" (c) y los consumos sin proveedor (i). Antes de la preparación, el control habría listado 22 movimientos de AgroNacion.
3. Exportar el control y comprobar que reproduce la pantalla.

## 7. Cruce de la devolución del débito (historia 4)

1. En el control, sección de sugerencias: devolución BNA 9426 del 17/09/2025 ($966.654,20) contra el débito BNA 18093 del 01/09/2025.
2. Aprobar el cruce. Esperado: la cuenta de AgroNacion suma una fila "Devolución" (deuda por $966.654,20) y las categorías (b) y (e) dejan de incluir ese caso.
3. Deshacer y volver a aprobar: queda registro de quién y cuándo en el historial.

## 8. Cruce del kit Starlink (FR-019)

1. Sugerencia: ingreso de Mercado Libre 20 del 20/08/2024 ($249.999,00) contra la línea 505 de Visa Galicia del 15/08/2024.
2. Aprobar. Esperado: la línea 505 pasa a "cruzado con devolución"; deja de figurar en (i); la deuda de la tarjeta se mantiene.

## 9. Mercado Pago (historia 5)

1. En Tesorería, movimientos de Mercado Libre: los 30 pagos de UATRE emparejados se marcan "conducto" (`esConducto`).
2. La cuenta de UATRE muestra el pago del 04/09/2024 ($17.185,82) y cada otro pago mensual una sola vez.
3. El saldo de la billetera coincide con el último saldo informado por Mercado Pago ($0,14).

## 10. Flujo de caja sin cambios (FR-017, SC-007)

```text
python -m pytest tests/test_vista_cuenta_tarjetas.py -k flujo -q
```

Esperado: los totales del flujo de caja real de varios períodos son idénticos antes y después (el módulo no consulta las ramas nuevas).

## 11. Pruebas automáticas y verificación del frontend

```text
cd backend && python -m pytest tests/test_tarjetas_cuenta_control.py tests/test_tarjetas_cuenta_cruces.py tests/contract/test_tarjetas_cuenta_api.py -q
cd ../frontend && npx tsc --noEmit
```

Esperado: todo en verde. Las pruebas de control y de cruces usan fixtures puros y no escriben en `WC`.

## Reversión

`python -m scripts.vista_tarjeta_cuenta_corriente --revertir` restaura la definición previa de la vista y quita las ramas nuevas; las tablas nuevas pueden eliminarse sin efecto en el resto. Los pagos reasignados se devuelven con `python -m scripts.preparar_tarjetas_cuenta_034 --revertir`.
