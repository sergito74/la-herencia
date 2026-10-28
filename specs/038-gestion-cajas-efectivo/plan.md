# Plan de implementación: Gestión de cajas de efectivo

### Ampliación28/10 — canje socio

Reutilizar coordinador, BancoOperacionCaja, puente sin contacto, vínculo de tesorería y reversión. Nuevo tipo `canje_socio`, sin DDL ni pruebas reales; IdSocio queda en cabecera/Solicitud. Controlar fecha, importe, contacto bancario y aporte/retiro previo antes de preview y dentro del guardado bajo bloqueos comunes. Interfaz de una carga con efecto caja/banco y socio sin cambio. Contrato simulado antes de UI; TypeScript, lint focalizado y recorrido UI con API interceptada. Preservar cambios ajenos.

**Estado actual**: implementación completada; ver cierre y evidencias en quickstart.md y tareas en tasks.md.

Fecha: 22/10/2026. Spec: [spec.md](spec.md). Rama real: main; contexto Spec Kit: 038-gestion-cajas-efectivo.

## Summary
Ampliar 027 para operar tres cajas en pesos. Una operación coordina caja, pago/cobro, aplicaciones, socio y banco en una transacción. Conservar historia y comparar con Excel durante la convivencia. Condominio muestra únicamente movimientos documentados con Giamigli; la historia ajena/sin vínculo queda archivada y se conserva auditada.

## Technical Context
- Language/Version: Python (Ruff py313), TypeScript 5, Next.js 14 y React 18 existentes.
- Primary Dependencies: FastAPI, Pydantic, pyodbc, Tailwind y TanStack Query; sin nuevas dependencias.
- Storage: SQL Server WC, Decimal para importes, fecha operativa local y auditoría UTC.
- Testing: pytest con SQL simulado, compilación TypeScript y comprobación UI acotada. Sin pruebas que escriban producción.
- Target Platform / Project Type: aplicación web existente.
- Performance Goals: pago en menos de un minuto; páginas de hasta 200 movimientos.
- Constraints: respaldo verificado antes de DDL/carga masiva; preservar Access, historia y permisos 016; pesos únicamente.
- Scale/Scope: tres cajas, seis historias de usuario y miles de movimientos históricos.

## Constitution Check
Revisión inicial y posterior al diseño: conforme. WC es el único registro; permisos y transacción protegen las escrituras; contratos preceden UI; cambios aditivos y reversibles. No hay excepciones ni nuevas dependencias. El esquema vivo se verificará antes de implementar DDL: no se verificó en esta fase.

## Project Structure
- backend/src/features/cajas_efectivo/: ampliar router, schemas y repository; servicio coordinador nuevo.
- backend/src/features/aplicaciones_pago/, cuentas_socios/, traspasos_internos_tesoreria/: primitivas compartidas bajo una misma transacción.
- backend/scripts/: migración 038 idempotente y verificación del esquema.
- backend/tests/: pruebas 038 simuladas.
- frontend/src/app/finanzas/cajas-efectivo/[caja]/ y components/cajas-efectivo/: ampliar pantallas.
- frontend/src/services/cajasEfectivoApi.ts: contrato tipado.
- Documentación: research.md, data-model.md, contracts/api.md, quickstart.md; tasks.md generado, con puertas de contrato previas a UI.

## Secuencia de implementación
1. Lectura acotada del esquema real de WC y convenciones de signos. Inventariar todos los consumidores de Pagos efectivo. Registrar evidencia, respaldo verificado y migración aditiva.
2. Coordinador transaccional, permisos, idempotencia, pago/compra particular y aportes/retiros.
3. Traspasos, cobros, arqueos y anulación conjunta, con exclusiones centrales de movimientos anulados y bancos vinculados.
4. Importación en vista previa, resolución humana de coincidencias ambiguas y comparación al mismo corte. No editar Excel ni remigrar la historia.
5. Solo después de ejecutar satisfactoriamente la verificación SQL/API de cada historia, UI con MoneyInput/formatMoneda, TanStack Query y navegación a orígenes. Validación por contrato antes de habilitar operaciones.

## Complexity Tracking
Sin excepciones. La cabecera de operación y sus vínculos no forman un libro paralelo ni guardan un saldo independiente.

## Registro histórico de planificación
22/10/2026: Sergio pidió retomar desde Claude. Se leyó traspaso, guía, Constitución, spec aclarada y código; investigación auxiliar solo lectura exigida por speckit-plan. Se generó diseño, sin DDL, escrituras en WC ni cambios en Excel. No existe extensions.yml. Pendientes históricos 036 siguen en su traspaso. Siguiente fase: speckit-tasks y luego implementación.

## Corrección del análisis — 22/10/2026
Autorización de Sergio: corregir los siete hallazgos. Ver precisiones vinculantes en spec.md, data-model.md y contracts/api.md. Contrato SQL/API ejecutado y verificado es puerta antes de cliente/UI, no solo antes de habilitar botones. Añadir GastoCajaEfectivo/RepartosGastoCaja como origen no fiscal único integrado a costos, sin duplicar compras. Separar traspaso interno de aportes/devoluciones Condominio. Invalidación/desactualización de arqueos, saldo real frente a subtotal filtrado, compatibilidad numérica GET y opción A acotada quedan definidos. Siguiente fase: implementar las 57 tareas; esquema vivo aún pendiente de lectura.


## Corrección de alcance aprobada — 23/10/2026
Sergio reemplaza la conservación visible de toda la caja del Condominio por un registro exclusivo de relaciones con Giamigli. Ver [criterios, contrato y plan de corrección](limpieza-condominio-20261023.md). Históricos ajenos/sin vínculo documentado permanecen archivados, fuera de saldos, filtros y comparaciones operativas. El neto parcial no representa tenencia física ni deuda; no admite arqueos físicos. Una sola entrada de Condominio con cuenta de socio y movimientos vinculados, sin sumar ni duplicar sus efectos.
