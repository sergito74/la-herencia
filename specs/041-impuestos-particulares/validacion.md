# Validación documental — 041 Impuestos particulares

Fecha: 25/10/2026. Sergio autorizó corregir las ocho observaciones de speckit-analyze. Alcance de este tramo: documentación y tareas; sin implementación, DDL ni escrituras en WC, LaHerencia o Access.

## Resolución del análisis

| ID | Problema | Resolución documental | Tareas de implementación/verificación |
|---|---|---|---|
| I1 | Origen de devolución de 28 caracteres no cabe en varchar(20) | DevImpParticular, 16 caracteres; no ampliar columna compartida | T003–T005, T019–T020 |
| C1 | Edición de boleta puede invalidar sus cargas | 409 al cambiar Fecha/Importe/organismo/tipo con cargas vigentes; bloquear edición y creación en persistencia | T007–T008, T016, T028–T030 |
| C2 | Editar/anular Haber ligado deja devolución falsa | Proteger todas las entradas de socios/operación de origen; desvinculación explícita antes | T019–T020, T023, T028–T032 |
| U1 | Reparto y capacidad de Haber indeterminados | Importe nominal explícito por vínculo, limitado por carga y Haber; saldo actualizado independiente | T003–T004, T019–T025 |
| I2 | Reintentos pueden duplicar carga parcial/Haber | UUID y huella persistidos, 200 en reintento idéntico, 409 con cuerpo distinto; anulados nunca se reactivan | T003–T008, T011–T012, T019–T025 |
| U2 | Falta fuente de partida y regla para varios titulares | Consulta auxiliar sin columnas en Impuestos; padrón derivado único/ambiguo/sin cargas; Oscar siempre Condominio | T019, T022–T026 |
| U3 | Anulación con devoluciones/padrón sin definir | Anular vínculos, conservar Haber, recalcular padrón; IdVinculo histórico permite revincular | T003, T022, T028–T033 |
| U4 | Fecha cercana y selección de manual indefinidas | Tres días corridos sobre fecha histórica, socio/importe exactos, Manual/NULL y vigente; selección humana | T007, T010, T017 |

## Evidencia de lectura previa

- Esquema de WC consultado: MovimientosCuentaSocio.Origen varchar(20), IdMovimiento int y Fecha datetime2. No hubo escrituras.
- Caso 3206: Debe manual 3149 al 07/11/2017, 8852,10 nominales, 501,5354 USD, kg 0; Haber 3150 al 13/11/2017, 8852,10 nominales, 505,8343 USD, kg 0. La migración debe verificar el estado vigente y estos valores, no basarse ciegamente en identificadores.
- La diferencia histórica de 4,2989 USD no se corrige automáticamente para etiquetar el impuesto como devuelto nominalmente.

## Estado (implementación 2026-10-25)

- Esquema aplicado en WC con respaldo verificado `WC_impuestos_particulares_041_20261025_123544_626816.bak`; migración 3206 con respaldo `WC_impuestos_particulares_041_20261025_123637_926741.bak`. Resultado: carga 3 → Debe 3153 (Origen ImpuestoParticular, 501,5354 USD), manual 3149 anulado, vínculo 1 → Haber 3150, estado devuelto; saldo del Condominio sin cambios (−5.656.204,01 / US$ −131.931,98 / kg −1.228,86). Segunda inspección: migrado, sin escrituras.
- Lectura real (solo lectura): resumen de lista del 3206 = `aCargoDe` Cond LSC $8.852,10, devuelto, pendiente 0,00; ficha: a cargo de socios 8.852,10, parte empresa 0,00. Guardias verificadas: anular 3153/3150 y baja del 3206 devuelven MOVIMIENTO_VINCULADO_A_IMPUESTO / IMPUESTO_CON_CARGAS.
- Pruebas: 19 de `test_impuestos_particulares_041.py` + cuentas de socios + cajas 038/040 = 149 passed; impuestos + flujo de caja + revisión + endpoints de socios = 229 passed. `tsc --noEmit` y ESLint sobre impuestos/services sin errores.
- Frontend: `ImpuestoParticularPanel` en la ficha (carga por importe o %, avisos con confirmación explícita, devoluciones a Haber existente o nuevo, quitar vínculo, anular con motivo, UUID persistente entre reintentos); grilla con columna «A cargo de socio», estado y filtro.
- Pendiente: T038, verificación en navegador del flujo real.
