# Implementation Plan: Recibos de Proveedores y Órdenes de Pago (046)

**Branch**: `046-recibos-ordenes-pago` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

---

## 1. Arquitectura Técnica y Componentes

### 1.1 Backend (FastAPI / SQL Server `WC`)
* **Nuevo feature en backend:** `backend/src/features/ordenes_pago/`
  * `router.py`: Endpoints REST para CRUD de Órdenes de Pago, listado de facturas pendientes por proveedor, emisión y anulación.
  * `repository.py`: Consultas SQL parametrizadas sobre facturas pendientes (`dbo.Compras`), aplicaciones de pago (`dbo.AplicacionesPago`) y tablas de OP.
  * `schemas.py`: Modelos Pydantic para solicitudes y respuestas de OP y Recibos.
* **Integración en `documentos_nuevos`:**
  * Actualización de `MODULO["recibo"] = "pagos"`.
  * Endpoint `/api/documentos-nuevos` con soporte para el módulo `pagos` y enlace directo a la vista de conciliación de pagos.
* **Integración con `dbo.AplicacionesPago`:**
  * Reutilización de la lógica transaccional de la Spec 019 para que al liquidar una OP o aplicar un recibo, se generen automáticamente las imputaciones de fondos y saldos.

### 1.2 Frontend (Next.js 14 / React / Tailwind)
* **Página principal:** `frontend/src/app/finanzas/ordenes-pago/page.tsx`
  * Solapa 1: **Órdenes de Pago** (Listado, estados, filtro por proveedor, botón "Nueva Orden de Pago").
  * Solapa 2: **Recibos pendientes** (Bandeja de Documentos Nuevos con origen mail o carpetas).
* **Componentes:**
  * `FormularioOrdenPago.tsx`: Selector de proveedor, tabla interactiva de facturas pendientes con checkbox de selección e importe parcial/total, selector de medios de pago previstos.
  * `VincularReciboModal.tsx`: Modal para comparar el PDF del recibo con la OP o transferencias candidatas y confirmar con un click.
  * Navegación en `NavHeader.tsx`: Acceso directo desde el menú **Finanzas → Órdenes de Pago y Recibos**.

---

## 2. Plan de Fases de Implementación

### Fase 1: Tablas de Base de Datos y Repositorio Core
1. Script de migración en `WC` para crear las tablas de soporte:
   * `dbo.OrdenesPago`
   * `dbo.OrdenesPago_Detalle`
   * `dbo.OrdenesPago_Medios`
   * Respaldo previo verificado con `COPY_ONLY` / `CHECKSUM` según constitución.
2. Repositorio backend con tests de contrato sobre listado de facturas pendientes y alta de OP.

### Fase 2: Ingesta de Recibos hacia el módulo de Pagos
1. Modificar clasificador y router de `documentos_nuevos` para rutear comprobantes de tipo `recibo` a `modulo="pagos"`.
2. Actualizar tests unitarios del clasificador.

### Fase 3: Conexión con Aplicaciones de Pago (Spec 019)
1. Servicio de ejecución de OP: cuando los débitos bancarios reales impactan en Tesorería, la OP pasa a `Pagada` y genera las filas correspondientes en `dbo.AplicacionesPago`.
2. Vinculación del PDF del recibo a la aplicación.

### Fase 4: Frontend y Flujo de Usuario
1. Implementación de las páginas y componentes en Next.js.
2. Pruebas de integración E2E / smoke test interactivo.


### Fase 5: Retenciones de Ganancias (Historia 4, agregada 30/10/2026)
- Tablas `RetencionesGanancias_Padron`, `_Conceptos` (rubro → régimen, con estado), `_Exclusiones`, `OrdenesPago_Retenciones` y la columna `OrdenesPago.RetencionGanancias`, con respaldo verificado (`scripts/retenciones_046.py`).
- `backend/src/features/retenciones_ganancias/`:
  - `simulador.py`: endpoints JSON públicos de calc-rg830, con GET previo por la cookie.
  - `padron.py`: zip público de condición tributaria, filtrado a los CUIT propios.
  - `repository.py`: condición del proveedor, base por régimen y acumulación mensual.
  - `mail.py`: borrador .eml para el estudio.
- CUIT faltantes completados desde los PDF de las facturas (`scripts/cuit_desde_facturas_046.py`).
- Calibración contra `Detalle de Pagos.xlsx` 2025-2026.

### Fase 6: Recibos con retención y anticipos (Historia 5)
- Columnas `RecibosProveedores.Retencion`, `Anticipo` y `CertificadoRetencion` (respaldo verificado antes).
- `vincular`: total = aplicaciones + retención + anticipo. Con OP, los pagos suman el neto y la retención es la de la OP.
- La pantalla de vinculación agrega retención (precargada desde la OP), número de certificado y anticipo.
