# Relevamiento y decisiones

Fuente de solo lectura: `C:/Users/Sergio/Documents/La Herencia/Administracion y gestion/Personal/Planilla trabajos eventuales.xlsx`, seis hojas: Trabajos, Hoja1, Recibo, Encabezado, Detalles y Empleado. Lectura XML del XLSX, conservando valores calculados y fórmulas como evidencia; sin recalcular ni modificar el archivo.

75 trabajos entre 07/09/2022 y 10/07/2026, total $2.500.558, todos Pagado; 26 sin número de recibo. Ocho personas: Mori 51, Rodríguez 5, Salvatierra 2, Palma 2, Alberto Gorosito 3, Mario Gorosito 2, Torrontegui 4, Pardo 6. Totales H72:H76 usan ROUNDUP, diferencias .25/.75; se preservan.

Hoja1: acuerdo Mori total $688.825, por recibo $313.298, fuera $375.527. Es una cuenta auxiliar que no se agrega a Trabajos: sumarla duplicaría labores. Recibo es plantilla de impresión del número 24. Encabezado contiene números 1–24 con varios vacíos; Detalles tiene recibos 1–4, en parte repetidos de Trabajos. Conservar fuente completa en copia externa y cabeceras/detalles en registro de importación.

WC no tiene tabla de eventuales. Existen cinco contactos por CUIT: 376 Mori, 379 Rodríguez, 415 Torrontegui, 519 Alberto Gorosito, 632 Pardo. Resolver los otros tres con padrón completo por CUIT antes de crear contactos con evidencia de Empleado. Ya hay liquidaciones y pagos históricos, incluidos ajustes aprobados en `franco_mori_sueldos_2022_036.py` y `cierre_mori_20261017.py`; no alterarlos. El historial contiene períodos libres, por lo que no debe vincularse por fecha/importe solamente.

Decisión: tablas propias para labores y vínculos operativos; Remuneraciones sigue siendo el único origen de deuda salarial. Rechazar exceso sobre neto real y sobre total del trabajo, en transacción con bloqueo central. Sin nueva rama ni cambios ajenos; preservar el trabajo existente y los archivos de la otra sesión. No hay hooks .specify/extensions.yml. Todas las dudas funcionales críticas resueltas por Sergio en chat y volcadas en spec.md. No quedaron investigaciones abiertas que requieran delegación.
