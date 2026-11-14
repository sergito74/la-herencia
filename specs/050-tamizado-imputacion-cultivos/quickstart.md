# Quickstart — validación de 049 + 050

## Requisitos

- Backup verificado de WC antes de `crear_tablas_tamiz_050.py` y de `activar_alcance_050.py --aplicar`.
- Reinicio del sistema con `LaHerencia.ps1 -Reiniciar -NoBrowser`.

## 1. Tests

```powershell
cd backend; python -m pytest tests/test_tamiz_050*.py tests/test_vinculo_auto_050.py tests/test_costos_alcance_050.py -q
```

Lo que tiene que pasar:
- Prioridad manual > orden > producto > rubro > revisión.
- Una factura mixta clasifica cada renglón por separado.
- Silobolsa: la orden decide el destino según su cultivo (grano → Comercialización, forrajero → ese cultivo, centro Ganadería → Ganadería).
- Una entrega parcial (100 + 100 contra 200) vincula los dos remitos.
- Una factura sin remito genera una capa virtual, y la capa desaparece cuando llega el remito.
- Los renglones fuera de alcance no aparecen en las fracciones `Directo` ni pierden su costo heredado.

## 2. Informe de impacto (sin escribir nada)

```powershell
python scripts/activar_alcance_050.py --dry-run
```

Genera un Excel antes/después por cultivo/campaña. Lo que se verifica:
- Las campañas sin renglones en alcance dan $0,00 de diferencia.
- Las diferencias están explicadas renglón por renglón.

Se le muestra a Sergio y recién con su OK se corre `--aplicar`.

## 3. Ejemplo glifosato (prueba de punta a punta)

Se hace con una factura real nueva, no con datos de prueba:

1. Cargar la factura de 200 l de glifosato. El renglón muestra "Va a stock" y la imputación queda 100% en stock.
2. Cargar o vincular su remito, y verificar que el vínculo se crea solo.
3. Ejecutar una orden que usa 80 l en Soja 2026/27. El renglón queda con 80 l → Soja 2026/27 y 120 l en stock.
4. Verificar en todo momento:
   - usos + stock = total, al centavo;
   - el resultado de Soja 2026/27 suma una sola vez;
   - el contador de "Para revisar" no sube si no hubo dudas.

## 4. Control diario

```powershell
python scripts/imputacion_diaria_050.py
```

Corre la pasada diaria. Al terminar se verifica:
- No quedan renglones en alcance sin clasificar: cada uno tiene destino o está en revisión.
- El control comprado = aplicado + stock + bajas, por producto y campaña, da diferencia 0 o la lista.
