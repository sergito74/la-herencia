# Implementation Plan: Lector general de facturas electrónicas

**Branch**: `main` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

## Summary

Agregar un lector de último recurso a la rutina 043: lee factura/ND/NC electrónicas, valida con reglas estrictas, deduce la imputación de las últimas 3 facturas del proveedor y carga con el mismo circuito de la bóveda. Corre primero solo en simulación; la carga real se habilita con una marca después de cumplir SC-001.

## Technical Context

**Language/Version**: Python 3.13, FastAPI; Next.js + TypeScript
**Primary Dependencies**: pdfplumber y pypdfium2 (ya instalados). Sin dependencias nuevas.
**Storage**: SQL Server WC; un parámetro nuevo de activación (ver data-model)
**Testing**: pytest con PDFs/textos simulados; simulación de solo lectura contra WC
**Constraints**: centavo exacto; nunca crear contactos; sin escrituras reales hasta aprobar la simulación
**Scale/Scope**: decenas de comprobantes por mes

## Constitution Check

- I/II: escribe solo en WC por el circuito de Compras; la simulación no escribe. PASS
- III/IV: cada carga conserva archivo, origen y aviso de revisión. PASS
- V: contrato interno en contracts/, pruebas antes de activar. PASS
- VI: la validación contra cargas manuales cumple la verificación de dominio. PASS
- VII: módulo aislado, apagado por defecto, reversible. PASS
- VIII: mismo stack. PASS

Post-diseño: sin cambios.

## Project Structure

```text
backend/src/features/documentos_nuevos/lectores/general.py   # lectura, validación, imputación
backend/src/features/documentos_nuevos/lectores/__init__.py  # último recurso tras los específicos
backend/src/features/documentos_nuevos/rutina.py, carpetas.py # usan el resultado
backend/scripts/simular_lector_general.py                     # informe contra cargas manuales
backend/tests/documentos_nuevos/test_lector_general.py
```

## Complexity Tracking

Sin violaciones.
