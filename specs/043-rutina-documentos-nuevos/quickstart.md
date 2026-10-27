# Quickstart / validación: 043 — Rutina automática de documentos nuevos

Prerrequisitos: backend y frontend levantados en la computadora de la oficina, Outlook abierto, respaldo de `WC` verificado antes de aplicar `backend/scripts/crear_esquema_rutina_043.py`.

## 1. Esquema

- `python -m scripts.crear_esquema_rutina_043 --verificar` → informa qué se crea, no escribe.
- `python -m scripts.crear_esquema_rutina_043` → respaldo + tablas de [data-model.md](data-model.md).

## 2. Rutina (sin esperar al horario)

- Adelantar `Rutina_Programacion.ProximaCorrida` a ahora (solo para la validación) y esperar el próximo minuto.
- Esperado: una fila en `Rutina_Corridas` que termina `ok` o `con_problemas`; una corrida por cada cuenta sincronizable en la bóveda; `Rutina_MarcaMails` adelantada por almacén.
- Repetir: la segunda corrida no vuelve a procesar los mismos mails ni crea avisos repetidos (SC-004, SC-006).

## 3. Mails

- Enviarse a la casilla un mail con una factura PDF de un proveedor conocido y otro con un PDF que no sea comprobante.
- Esperado: la factura queda en la carpeta de Compras del ejercicio y en el aviso de Compras; el otro PDF se ignora (Clarification 1). Ningún mail queda marcado, movido ni borrado.
- Un comprobante de un emisor no registrado queda "para cargar a mano" con "Emisor nuevo".

## 4. Avisos y revisión

- El menú muestra el número en Compras (y en Ventas/Finanzas según corresponda); el clic abre "Nuevos para revisar" con el primero abierto ([contracts/api.md](contracts/api.md)).
- "Revisado" baja el número; "Ver compra" abre la compra; un "sin clasificar" se puede mover a su módulo.
- La pantalla de la bóveda ya no muestra el listado "Cargado solo en Compras — para revisar".

## 5. De Campo a Campo

- Sincronizar la cuenta: solo aparecen liquidaciones/retenciones de Giamigli; **ninguna operación de Ganadera San Justo** se lista ni se baja.

## 6. Verificaciones automáticas

- Pruebas de contrato de `/api/documentos-nuevos` con datos simulados (sin escribir en `WC`).
- Pruebas unitarias del clasificador (tipo, emisor, receptor) con textos de PDF de ejemplo y de la marca de mails.
- `npx tsc --noEmit` del frontend.
