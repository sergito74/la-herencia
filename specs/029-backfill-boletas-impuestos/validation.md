# Validación 029

Baseline: rama 029-backfill-boletas-impuestos, commit 222849b; cambios previos preservados en agent-guidance y carpeta specs/029. Python 3.13.0, Node 24.16.0; entornos existentes, sin instalación. Checklist requirements: 16 completos / 0 pendientes.

Relevamiento SELECT: seis tablas de pago, claves/signos coinciden con adaptadores de 023/024. Tapalqué: Compras 10 movimientos, deuda 49.615,60; BNA crédito 14.401,40; Galicia deuda 17.642,00 y crédito 51.000,20; efectivo crédito 1.856,00. Saldo cero explicado por otros documentos y entradas: no generar boletas automáticamente.

Implementación y pruebas en curso. Ninguna carga de boletas autorizada todavía: requiere propuesta concreta revisada.

## 2026-09-30 — Retoma (Claude) sobre el trabajo de Codex

**Cambio de criterio decidido por el usuario** (el motor original no generaba ninguna boleta para AFIP/ARBA/Bolívar/UATRE):
1. Una boleta ya cargada del mismo organismo, mismo importe (±$0,10) y fecha a ≤90 días respalda al pago sin vínculo explícito; asignación uno a uno por cercanía de fecha.
2. Segunda pasada de absorción: boletas abiertas sin coincidencia exacta, otros documentos de la cuenta (ej. Compras) y reintegros del organismo cubren a los pagos de fecha más cercana; solo se genera boleta por lo descubierto (`importeAGenerar`).
3. AFIP queda fuera de la generación (su saldo mezcla ~$18,16M de devoluciones de IVA granos); se diagnostica igual.

**Identidad verificada contra WC**: saldo a favor = pagos sin coincidencia − boletas abiertas − otros documentos (± reintegros), al peso en los seis organismos.

**Diagnóstico real (solo lectura)** — total a generar = saldo a favor, saldo proyectado 0:

| Organismo | A generar | Generadas | Con comprobante | Comprobante a elegir |
|---|---|---|---|---|
| ARBA | $6.367.489,00 | 27 | 2 | 7 |
| Municipalidad de Bolívar | $5.441.161,44 | 9 | 1 | 4 |
| UATRE | $874.637,64 | 8 | 0 | 0 |
| Ministerio de Desarrollo Agrario | $6.000,00 | 1 | 0 | 0 |
| Municipalidad de Tapalqué | $0 (saldo ya en cero) | — | — | — |
| AFIP | — (fuera de la generación) | — | — | — |

**Otros arreglos**: inventario de comprobantes (rutas heredadas "ruta#ruta#" relativas a Compras, nombres pegados tipo `MunicipalidadDeBolivar`, alias `IIBB`→ARBA y `TasaVial`→Bolívar, solo se hashean candidatos: pasó de >30 s cortado a 1-3 s); backup verificado desde un botón en la pantalla; formato de importes con `formatMoneda`.

**Migración** aplicada con backup verificado `558edc2f-0065-4206-a286-e38789378167` (C:\Temp\LaHerencia029). **Ningún lote confirmado todavía** (T038 espera la revisión del usuario). Suite backend: 757 tests OK; `tsc` y `eslint` limpios en lo tocado.
