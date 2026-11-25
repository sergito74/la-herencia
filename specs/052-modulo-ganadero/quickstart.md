# Quickstart: validación del Módulo Ganadero (etapa 1)

## Requisitos
- El backend y el frontend corriendo (`launcher/LaHerencia.ps1 -Reiniciar -NoBrowser`).
- Un respaldo verificado de WC antes de correr los scripts con `--aplicar`.

## 1. Esquema
```
cd backend
python -m scripts.ganaderia_tablas_20261125            # simula
python -m scripts.ganaderia_tablas_20261125 --aplicar  # crea Gan*, EsGanaderia, semillas de categorías, alias, rubros y calendario
```
Esperado: las tablas creadas, y `Map_CultivoResultado.EsGanaderia = 1` en los 6 cultivos forrajeros.

## 2. Forrajes fuera del Resultado de cultivos (SC-005)
- **Antes:** anotar el costo agrícola total de 2023/24 en el Resultado de cultivos.
- **Después:** el costo agrícola baja en un importe X, y `GET /api/ganaderia/resultado?vista=campania` muestra en Alimentación el mismo X, al centavo.
- **Prueba:** `pytest backend/tests/ganaderia/test_forrajes_traspaso.py`.

## 3. Resultado vs planilla (SC-001a)
- `GET /api/ganaderia/resultado?vista=campania&moneda=USD&desde=2018/2019&hasta=2018/2019`
- **Esperado:**
  - Venta total S/IVA = US$ 37.677;
  - Vacunas = 2.270;
  - Inseminación = 1.253;
  - Productos veterinarios = 494.
- **Lo mismo para 2022/23:**
  - Ventas = US$ 91.191;
  - Vacunas = 2.417;
  - Inseminación = 1.736.
  - Las diferencias de productos veterinarios, aranceles, flete y pastaje se listan.

## 4. Ha ganaderas (FR-013)
`GET /api/ganaderia/superficie?periodo=2026/27`: los lotes de pastura y avena del plan 26/27 (1A, 4, 7B1, 7B2, 8B, 9A1, 9B1, 9B2, 10A1, 10B) cuentan 12 meses. Los lotes agrícolas (3B soja 1.ª, etc.) cuentan solo los meses de rastrojo.

## 5. Stock histórico (FR-007, SC-003)
```
python -m scripts.ganaderia_stock_historico_20261125            # simula: lista recuentos y alias sin resolver
python -m scripts.ganaderia_stock_historico_20261125 --aplicar
```
- `GET /api/ganaderia/stock?fecha=2023-10-26` = 248 vacas, 20 toros, 7 toritos, 133 terneros, 96 terneras (La Herencia).
- `GET /api/ganaderia/stock?fecha=2026-10-15&dueno=terceros` = 70 vaquillonas de San Justo.

## 6. Venta → movimiento
Al editar y guardar una venta existente se genera o actualiza un solo movimiento por renglón: la venta 0003-00010318 da 2 vacas y 880 kg. Al borrar la venta se anula el movimiento.

## 7. Controles
`POST /api/ganaderia/controles/correr`: aparecen los grupos Ventas, Consignatarios, Stock, Pastaje e Imputación. Al aceptar un caso con motivo, ese caso desaparece de la lista y queda en "Revisados y aceptados".

## 8. UI
En `/ganaderia/resultado`:
- las cifras usan miles con '.' y decimales con ',';
- un período sin dato muestra "—";
- al hacer clic en una celda se abre el detalle con sus comprobantes;
- en pantalla no aparece ningún id ni código.
