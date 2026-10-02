# 033 — Alta, edición y baja de boletas de impuestos

**Estado**: implementado 2026-10-02 · **Pedido por**: Sergio

## Contexto

El módulo de Impuestos (005) nació de solo lectura (FR-008 de 005). Al
conciliar la tarjeta Visa Galicia quedó un pago a ARBA de $312.351,20
(29/02/2024) sin boleta, y no había forma de cargarla desde el sistema.
Ya se sabía que faltan muchas boletas de impuestos: se cargaron los pagos
pero no los documentos (ver nota "impuestos con boletas faltantes").

Esta funcionalidad **reemplaza el FR-008 de 005** para la tabla
`dbo.Impuestos`: el módulo pasa a permitir alta, edición y baja de boletas.
Las retenciones siguen siendo de solo lectura.

## Historias

1. **Cargar una boleta** (P1): desde Impuestos, "Nueva boleta" abre un
   formulario con organismo, tipo de impuesto, fecha, período liquidado,
   número de documento, importe y ruta del documento original. Al guardar,
   la boleta aparece en el listado y como deuda en la cuenta corriente del
   organismo, lista para conciliar contra el pago (tarjeta o banco).
2. **Corregir una boleta** (P1): desde el listado, abrir una boleta y
   editar cualquier campo.
3. **Eliminar una boleta cargada por error** (P2): con confirmación. Si la
   boleta ya está vinculada a un consumo de tarjeta o tiene aplicaciones de
   pago, no se puede eliminar hasta quitar esos vínculos.

## Requisitos

- **FR-001** Organismos disponibles: los de la referencia de impuestos
  (`docs/referencia-impuestos.md`): AFIP/ARCA (contacto 119), ARBA (12),
  Municipalidad de Bolívar (72), Municipalidad de Tapalqué (422), UATRE (315).
- **FR-002** El tipo de impuesto se elige del catálogo `[Tipo Impuesto]`
  filtrado por el organismo elegido (código heredado 1=AFIP, 2=ARBA,
  3=Bolívar, 4=Tapalqué; el tipo 15 "Aporte Sindical" es UATRE). No se
  ofrecen "Retenciones Ganancias" (no es impuesto propio) ni "Sin
  identificar (generada desde el pago)".
- **FR-003** Obligatorios: organismo, tipo, fecha, importe distinto de 0.
  Opcionales: período liquidado, número de documento, documento original.
- **FR-004** Duplicado: se bloquea otra boleta del mismo organismo con el
  mismo número de documento **si el número tiene algún dígito** (mismo
  criterio que Compras: "SIN COPIA", "S/D" no identifican un comprobante).
- **FR-005** Baja bloqueada si la boleta tiene vínculos con consumos de
  tarjeta o aplicaciones de pago vigentes.
- **FR-006** Solo usuarios con permiso de escritura (rol distinto de
  `Lectura`); el backend ya rechaza escrituras de ese rol.
- **FR-007** Todas las escrituras van a `WC`.

## Fuera de alcance

- Carga masiva / backfill de boletas faltantes (tarea aparte).
- Vincular la boleta al pago desde este formulario: se hace como hasta
  ahora, desde la conciliación de tarjetas o tesorería.
