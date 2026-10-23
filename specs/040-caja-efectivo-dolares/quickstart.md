# Verificación y continuidad — 040

## Aplicado en WC
Migración `backend/scripts/migrar_caja_dolares_040.py --aplicar`, 23/10/2026. Nuevo valor de caja GiamigliUSD, CHECKs ampliados y seis filas históricas originales; no se crearon operaciones financieras de prueba.

Respaldo con CHECKSUM y RESTORE VERIFYONLY antes de escribir:
`C:/Program Files/Microsoft SQL Server/MSSQL17.SQLEXPRESS/MSSQL/Backup/WC_caja_dolares_040_20261023_102436_704182.bak`.

Evidencia: `backups/caja-dolares-040/migracion-20261023-102437.json`, con SHA256 de fuente, restricciones originales, filas y saldos anteriores/posteriores.

| Caja | Filas antes/después | Saldo antes/después |
|---|---:|---:|
| CampoChica | 100 / 100 | $96.907,00 |
| CondominioLSC | 1.226 / 1.226 | $0,23 |
| GiamigliSA | 2.024 / 2.024 | $381.785,15 |
| GiamigliUSD | 0 / 6 | US$360,00 según planilla |

Lecturas reales de repository, caja_context y función API de saldo confirman seis filas y saldoDecimal 360.00, sin arqueos todavía. Este saldo reproduce la planilla, no certifica un recuento físico actual.

## Comprobaciones
- 65 pruebas focalizadas de 040, contratos base/socios/importador 038 y repositorio socios: PASS. Luego 18 de USD/importador: PASS al corregir que la columna de pesos no se use como número de documento.
- TypeScript --noEmit y ESLint de componentes/cliente/rutas afectados: PASS.
- Ruff de los dos archivos nuevos con --ignore E501: PASS; E501 se conserva para SQL embebido.
- No hay lectores de MovimientosCajaEfectivo fuera del módulo que sumen cajas sin separar moneda.

## Uso
Finanzas → Cajas y socios → Giamigli US$. Saldo, entradas/salidas, aportes/retiros y arqueos son US$ billete. Desde la cuenta del socio también puede elegirse Giamigli US$.

Los seis movimientos históricos están identificados por Caja+FilaPlanilla. Comparar la hoja reconoce esas filas; no volver a cargarlas como nuevas operaciones ni inferir de ellas asientos de socios. Las tres ventas de dólares no autorizan tratar a los compradores como aportantes/retiros.

## Reproducción del navegador
Usar frontend con `NEXT_DIST_DIR=.next-cajas040` y un puerto libre, y `CAJAS_UI_URL=http://127.0.0.1:PUERTO` al ejecutar `backend/tests/ui/cajas_038_smoke.py`. No requiere backend: todas las API se interceptan. Asegurar ejecutar Next desde frontend para cargar Tailwind. Capturas y resultado: `backups/cajas-038-ui/` (ignorados por Git).

## Límites vigentes
No se habilitan transferencias 1:1 entre monedas ni aplicaciones fiscales/bancarias USD sobre circuitos en pesos. Las conciliaciones 036, el DTe de pastaje y las otras hojas pendientes del traspaso no se tocaron.

## Navegador final
PASS en Edge headless: 20 escenarios, 123 API interceptadas, cero errores JavaScript y cero API sin fixture. Incluye resumen, caja USD, aporte desde Lucy a caja USD, alta/edición/anulación de asiento, rol Lectura en caja y socio, y corrección de caja conservando aplicaciones. Se verificó también que Tailwind esté cargado y se inspeccionó visualmente la captura de la entrada USD; muestra +US$100 en la previsualización.

Resultado y capturas en `backups/cajas-038-ui/resultado.json`, `resumen-cajas-socios.png`, `dolares-preview.png`, `socio-aporte-dolares.png`, `socio-solo-lectura.png`. Los saldos de estas capturas son simulados y no representan WC. La consulta real separada devuelve US$360 según fuente.

Se usó servidor aislado en puerto 3104 con NEXT_DIST_DIR; el agregado automático de Next a tsconfig se retiró al terminar. No se cambiaron dependencias ni archivos de datos de origen. Las capturas anteriores durante el ajuste del servidor de pruebas se reemplazaron por las del recorrido final con CSS comprobado.
