# Quickstart: validar la auditoría de cuentas corrientes

Todo en `WC`. Desde `backend/`, con `PYTHONIOENCODING=utf-8`. Referencias: [data-model.md](data-model.md) y [contracts/auditoria-cuentas-api.md](contracts/auditoria-cuentas-api.md).

## Preparación

1. Crear las tablas (primero en modo verificación, que no escribe): `python -m scripts.crear_esquema_auditoria_035 --verificar`, luego sin opción (respaldo verificado y tablas, idempotente). Esperado: tablas `AuditoriaParametros` (con 3 valores iniciales), `AuditoriaCorrecciones` y `AuditoriaCorreccionesCuentas` vacías.

## Pasos de validación

1. **Parámetros (D8)**: `GET /api/auditoria-cuentas/parametros` devuelve plazo 24, umbral 300 y anticipo 60.
2. **Reproducción del 01/10 (SC-005)**: `GET /resumen` informa 513 cuentas, 436 que coinciden (incluidas "coincide con causa conocida") y el resto agrupado; ninguna de las 436 cambia de grupo después de una corrección. Si no se reproduce, se ajusta la lista de fuentes antes de seguir.
3. **Casos conocidos (SC-002)**: sin señalarlos, aparecen Cargill (movimiento Galicia 3240, contacto 258, plazo), Cooperativa y Lartirigoyen (doble descuento con tarjeta) y Nidera (nota sin imputar).
4. **Medición del plazo (D1)**: los hallazgos de plazo coinciden con la medición previa: 2.194 aplicaciones `automatica-exacta` (BNA 1.477, Galicia 717) en unos 110 contactos, agrupadas por movimiento.
5. **Todas las cuentas clasificadas (SC-003)**: la suma de cuentas de todos los grupos es igual al total de cuentas con referencia; "otros" nunca queda oculto.
6. **Cambio de plazo**: `PUT /parametros` con 12 aumenta los hallazgos de plazo; volver a 24 los devuelve al valor anterior.
7. **Corrección (SC-007)**: simular `anular-doble-descuento-tarjeta` (sin cuentas tildadas), tildar una cuenta, aplicar (queda el respaldo), verificar `saldoAntes = saldoDespues`, que la cuenta sale del grupo y que revertir la devuelve al grupo y deja las aplicaciones exactamente como estaban.
8. **FIFO completo (SC-004)**: crear la simulación con todos los contactos desde Finanzas → Recálculo FIFO; revisar las que no cierran; aplicar por tandas y confirmar que el saldo de cada cuenta es idéntico antes y después.
9. **Exportación**: exportar un grupo y comparar con la pantalla.
10. **Solo lectura**: con rol `Lectura` se ve y se exporta el control, pero aplicar y revertir responden `403` y los botones no aparecen.

## Pruebas automáticas

- `python -m pytest tests/test_auditoria_clasificacion.py tests/test_auditoria_correcciones.py tests/contract/test_auditoria_cuentas_api.py -q`
- `npx tsc --noEmit` en `frontend/` y `node tests/auditoria-cuentas.e2e.cjs` con el servidor en el puerto 3100.
- Suite completa: `python -m pytest tests -q` debe seguir pasando.

## Resultados de la corrida

**Preparación (06/10/2026):** esquema creado con respaldo `WC_esquema-auditoria-035_20261006_184649` (tablas de parámetros, correcciones y referencia fila a fila; parámetros 24 / 300 / 60); referencia cargada con respaldo `WC_referencia-detalle-035_20261006_184651`: 17.765 filas, igual a `SaldoAccess` en los 513 contactos.

**Historia 1:** 495 cuentas comparadas: 292 coinciden, 177 coinciden con causa conocida, 6 con diferencia menor al umbral, 4 sin referencia y 16 en "otros"; respuesta en 1,4 s (SC-001). 14 pruebas pasan y `npx tsc --noEmit` sin errores.

**Historia 2 (06/10/2026):** con plazo de 24 meses, 114 cuentas tienen pagos aplicados fuera de plazo (1.541 hallazgos agrupados por movimiento, $144,8 M aplicados; todos de aplicaciones automáticas), 22 hallazgos de aplicaciones del FIFO quedan en el grupo "decidido a mano o por FIFO" que no cuenta como excepción, 125 hallazgos de doble descuento con tarjeta en 21 cuentas ($1,26 M), 10 notas de débito sin imputar en 7 cuentas y 3 contactos con el mismo CUIT. Cargill (258): el movimiento 3240 de Galicia aparece con 104 facturas desde el 07/05/2019 ($5,38 M de lo aplicado superan el plazo). Cooperativa (22) y Lartirigoyen (61) aparecen con doble descuento (4 y 6 casos). Nidera: la nota 7028-00011189 ya figura imputada ($180.411,30), por lo que ya no es un caso (la memoria estaba desactualizada). No hay sobrepagos. Detección en 0,4 s. 25 pruebas pasan.

**Causas restantes (06/10/2026):** los organismos (AFIP, ARBA, municipios, SENASA, UATRE y otros) pasan a ser cuentas auditables: 505 cuentas comparadas (483 coinciden, 18 en "otros"); 7 organismos tienen más pagado que boletas cargadas ($29,7 M: AFIP $14,2 M, ARBA $7,3 M, Municipalidad de Bolívar $6,6 M, Consejo de Ciencias Económicas $0,8 M, SENASA $0,09 M, Min. Desarrollo Agrario $6.000, UATRE). Movimientos sin contacto de $100.000 o más: los de más de $100.000 son impuestos y comisiones del banco, fondos comunes, plazos fijos y transferencias propias, más la devolución del Banco Nación 9426 ya cruzada; no queda ninguno por revisar. 951 pruebas pasan.

**Mecanismo de lo conocido (06/10/2026):** sin umbral de importe. De unos 6.000 movimientos sin contacto, las 11 reglas iniciales explican unos 5.860 (impuestos del banco 5.770, fondos comunes 37, depósitos 19, bancos propios 21, plazos fijos 5, otros); quedan 167 movimientos en 30 grupos por concepto ($0,82 M) para decidir una regla por grupo. Las diferencias de cuentas se documentan con su motivo desde el grupo "otros". 956 pruebas pasan.

**Revisión de una cuenta (06/10/2026, Historia 0):** pantalla `Finanzas → Auditoría de cuentas → Revisar cuentas`: lista de movimientos con saldo acumulado, enlace al PDF del comprobante y al origen, cambio de contacto, anular imputaciones (baja lógica con respaldo, reversible), cargar nota de ajuste (débito o crédito "SIN DOCUMENTO"), saldo esperado (cero o puede tener saldo), marca de revisada con nota y aviso si el saldo cambió después, historial y "Siguiente cuenta" en orden alfabético de las fáciles (228 sin avisos) a las complicadas (134). Prueba de navegador `auditoria-cuentas.e2e.cjs` OK, `npm run build` OK, 968 pruebas del backend pasan. Pendiente: T053 (asignar contacto a movimientos sin contacto uno a uno, por lotes y por regla).

**Criterio de moneda (07/10/2026, FR-024):** caso ArPov (contacto 454): factura US$ 216,70 al TC 96,69 ($ 20.952,45) y pago de $ 20.952,45 en Galicia; antes la cuenta mostraba un saldo de +$ 20.735,75 porque sumaba dólares con pesos y el pago aparecía como si fuera en dólares; ahora el saldo en pesos es $ 0,00 (en dólares −US$ 0,94: diferencia de cambio). 26 contactos tienen documentos en dólares (455 documentos): 5 solo en dólares y 21 bimonetarios; Cargill tiene un documento sin tipo de cambio (se estima con el BNA). La vista compartida no se modificó (el FIFO y los demás módulos siguen igual): el criterio es una capa de solo lectura de la auditoría.

**Moneda que gobierna (07/10/2026):** regla de Sergio: si el proveedor emite sus documentos en dólares gobierna el dólar; si en pesos, el peso. De las 26 cuentas con documentos en dólares, 5 son solo en dólares (ArPov, Palaversich, Tierras de Henderson, Galicia Seguros y San Cristobal): su saldo gobernante es el de dólares. Las 21 mixtas necesitan que el FIFO asigne cada pago a su documento: hoy las aplicaciones por documento cubren una parte chica de los pagos (por ejemplo Cargill: $18,5 M aplicados de $446,6 M pagados), por eso para las mixtas se muestran los dos saldos y se pide completar el FIFO (Historia 3) antes de dar un único saldo por moneda. 975 pruebas del backend pasan.

**Regla B y diferencia de cambio (07/10/2026):** Sergio confirmó que la regla general es la B: gobierna la moneda en que el proveedor emite y el tipo de cambio se ajusta con notas de crédito o de débito (son acuerdos comerciales: no hay un criterio único de "dar por saldado"). En las cuentas en dólares con una diferencia, la revisión avisa "diferencia de cambio" y ofrece cargar la nota por esa diferencia con el importe, el tipo y el dólar BNA ya completados (se puede cambiar antes de guardar). Casos: Palaversich 2023 (pesificó al entregar los cheques: US$ 342,06) y Tierras de Henderson (US$ 1.123,19). Las fechas de entrega de los e-cheques no están registradas en el sistema (la tabla de valores propios llega hasta 2014): la nota es el modo de dejar documentada la pesificación.

**Cheques entregados (07/10/2026, FR-025):** carga de `Cheques electronicos/` (149 PDF + planilla `Pagos Cheques Diferidos.xlsx`): 153 cheques (130 e-cheqs emitidos, 21 endosos de cheques de terceros, 2 en papel); 110 cruzados con débitos de Galicia; 18 PDF escaneados sin texto (cubiertos en su mayoría por la planilla); 20 con fecha de entrega estimada por la fecha del archivo. Efecto en dólares con el dólar del día de entrega: Palaversich 2023 pasa de −US$ 342,06 a −US$ 42,19; Tierras de Henderson de −US$ 1.123,19 a −US$ 2,21 (cheque entregado el 10/06/2021, el día de la factura): ya no necesita nota. La tolerancia en dólares es el mayor entre US$ 1 y el 0,5 % de lo facturado en dólares.

**Campo y Tecnología (contacto 493, 07/10/2026):** el saldo es +$ 6,92 (redondeo), pero las facturas no cerraban: de $ 2.102.329,86 facturados había $ 2.081.822,12 imputados (faltaban $ 20.507,74) porque los pagos de 2022 y 2024 estaban imputados a facturas equivocadas por las aplicaciones automáticas. La simulación FIFO (ejecución 34) deja todas las facturas cerradas, con un pagado de más de $ 6,92. Se aplica desde la revisión de la cuenta.
