# Quickstart: validar el recálculo FIFO

## Prerrequisitos

- El backend corre con `.venv` y la conexión a `WC`.
- El esquema está creado con `backend/scripts/crear_esquema_recalculo_fifo.py`. El script hace un respaldo antes de crear tablas.
- La serie `[Dolar BNA]` cubre los pagos a validar. Está completa hasta el 30/09/2026 y se actualiza con `backend/scripts/actualizar_dolar_bna.py`. Después de esa fecha, los renglones USD salen con la marca "TC implícito".

## 1. Tests del motor (sin base)

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/recalculo_fifo -q
```

Casos mínimos:

- **Anticipo:** un pago anterior a la factura cubre la factura.
- **Anticipo largo:** con más de 60 días, queda marcado.
- **Orden de cobertura:** se cubre primero el vencimiento más temprano. Con la misma fecha, el número de comprobante más bajo.
- **Cuotas:** se cubren en orden.
- **Cadena de tarjeta:** cubre una parte y el FIFO cubre el resto, sin anular la factura.
- **Elección explícita:** se respeta.
- **Factura suspendida:** se saltea.
- **Nota de crédito con factura de origen:** se aplica primero a esa factura.
- **Documento USD con pago en pesos:** se convierte al tipo de cambio del día anterior.
- **Compensación cruzada:** se hace en USD.
- **Pago de más sin débito posterior:** es una excepción.
- **Idempotencia:** dos corridas producen la misma huella.

## 2. Simulación de la primera etapa

Contactos complejos: 258 Cargill, 47 J y M de la Serna, 48 Jauregui y Morales, 23 Coop. Eléctrica Bolívar y 384 Ganaderos de Elordi.

Contactos simples: 340 Colombo y Colombo, 249 Supermercado Actual, 276 Autopistas del Sol y 220 Miguel Basterrechea.

```http
POST /api/recalculo-fifo/ejecuciones {"alcance":[258,47,48,23,384,340,249,276,220]}
```

Lo que se espera:

- `AplicacionesPago` no cambia. Comparar el conteo y la suma antes y después.
- 47, 384 y 340 siguen cerrando (SC-001).
- 249 y 276 quedan sin facturas sobreaplicadas.
- Cargill compensa ventas de granos contra compras en USD. Si no cierra, la excepción tiene que explicar por qué.

Revisión: el especialista financiero (07) valida los 9 contactos con Sergio antes de aplicar.

## 3. Aplicar, re-ejecutar y revertir

1. Aplicar la ejecución. Se espera un respaldo registrado y controles en verde en los contactos aplicados (SC-002).
2. Simular de nuevo los mismos contactos. Se espera la misma huella y que todos figuren `sinCambios` (SC-005).
3. Revertir. Se espera que `AplicacionesPago` sea idéntica a la de antes, con la misma suma, los mismos conteos y los mismos ids vigentes (SC-006).

## 4. Todos los contactos

Simular con `alcance: "todos"`. Se espera que termine en menos de 5 minutos (SC-007) y que al menos el 90% de los contactos pase los controles (SC-003).

## 5. Operatoria continua

1. Asignar contacto a un movimiento bancario de prueba en un contacto simple.
2. Llamar a `cola/procesar`. Se espera que la aplicación entre sola.
3. Consultar `saldo-por-vencimiento` de un contacto con cuotas. Se espera ver los tramos por fecha.
4. Simular un lunes. Se espera que el aviso de vencimientos aparezca una sola vez.

## 6. Rubro

En el flujo por rubro de un trimestre, la suma de los rubros tiene que ser igual a los pagos del período (SC-008).
