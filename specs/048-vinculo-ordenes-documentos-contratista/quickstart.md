# Quickstart / validación: 048 (revisado 06/11)

## Prerrequisitos

- Backup verificado antes de `backend/scripts/vinculos_contratista_048.py`.
- Foto previa de saldos de cuentas (sin caché) y del Resultado por cultivo, en el scratchpad.
- Reinicio con `LaHerencia.ps1 -Reiniciar -NoBrowser`.

## Escenarios

1. Editar la factura 00002-00000735 de Pérez: el panel "Órdenes de trabajo" lista sus órdenes; tildar la del 25/10/2026 y guardar. Se muestra el reparto, que suma el neto al centavo.
2. Abrir esa orden: muestra la factura (enlace a la compra) y el reparto, sin botones para vincular.
3. Resultado: el cultivo/campaña muestra el costo desde la orden y la factura no cuenta además por su carga manual.
4. Relacionar una NC de Pérez con una factura vinculada: la NC queda imputada con las mismas proporciones y en negativo; aparece en la orden.
5. Destildar la orden en la factura: la imputación se retira y vuelve la carga manual.
6. Factura de Yanquelen de hacienda: el panel no ofrece órdenes; no está en el listado "sin orden".
7. Guardar una factura de labor nueva sin órdenes: aparece el aviso.
8. Usuario de solo lectura: ve el panel sin poder guardar; el PUT responde 403.
9. Control final: saldos de cuentas y costo por campaña iguales a la foto previa (salvo repartos entre cultivos, que se listan).
