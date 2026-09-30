# Quickstart y validación — 029

Estado: guía para implementación futura; no hay endpoints ni migración 029 implementados. Los comandos de pruebas nombran archivos previstos, no una suite ya ejecutada.

## Preparación

1. Rama `029-backfill-boletas-impuestos`; leer spec, research, data-model y contrato API. Generar tasks y analizar consistencia antes de implementar.
2. Usar entornos existentes `backend/.venv` y `frontend/node_modules`. No instalar paquetes para este diseño.
3. Confirmar conexión limitada a WC. WC es producción: usar mocks/fixtures para escrituras automáticas; no ejecutar scripts históricos UATRE ni restaurar WC.
4. Configurar raíces documentales explícitas Impuestos/Compras y directorio privado de evidencia de backup fuera de Git; verificar archivos solo en lectura.
5. Para la carga futura: revisar POST validar, obtener preparacion firmado, ejecutar localmente `backend/scripts/crear_tablas_backfill_impuestos.py --backup-only --preparacion <token>` y refrescar GET /respaldo desde la UI. Este comando todavía debe implementarse. Solo confirmar cuando estado sea verificado y usando el mismo token/selección; un cambio requiere nueva preparación y backup. Reversión sigue el mismo circuito. No imprimir ni versionar tokens. El tiempo operativo del backup se informa separado del tiempo de revisión de SC-005.

## Verificación de implementación prevista

Desde backend, después de crear las pruebas:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_backfill_impuestos_diagnostico.py tests/test_backfill_impuestos_propuesta.py tests/test_backfill_impuestos_repository.py tests/contract/test_backfill_impuestos_api.py
```

Desde frontend:

```powershell
.\node_modules\.bin\tsc.cmd --noEmit
```

Ejecutar además las pruebas existentes de conciliación documental/Tarjetas afectadas por el nuevo saldo compartido. Las escrituras deben estar simuladas; comprobar que ninguna prueba usa WC real para insertar.

## Escenarios de aceptación

| Caso | Resultado esperado |
|---|---|
| Organismo sin faltantes / consulta vacía | cero propuestas, sin botón de carga activo |
| Pago cubierto por vínculo / solo contacto reconocido | primero respaldado; segundo se investiga, no se da por respaldado |
| Dos pagos y una boleta compatible / importe parcial | no reutilizar capacidad, casos ambiguos pendientes |
| Centavos 0,09 / exceso de imputación 0,02 | tolerancia de coincidencia no habilita sobreimputación |
| Reintegro, retención, traspaso, contacto 0 | excluido o pendiente con causa, ninguna boleta |
| Tapalqué con otros respaldos y saldo cero | explicación, sin generación automática por ausencia de Impuestos |
| PDF único / varios / repetido por hash / ya adjunto | propuesto / ambiguo / deduplicado / excluido |
| Raíz inexistente o recorrido interrumpido | no concluir ausencia de comprobante; impedir generación afectada |
| Pago totalmente descubierto sin tipo | una boleta total, fecha del pago, tipo genérico del organismo |
| Dos sesiones confirman pago / reintento de UUID | un único lote efectivo; conflicto o respuesta idempotente |
| Fuente modificada tras revisión / falla entre inserts | conflicto o rollback completo; cero carga parcial |
| Rol Lectura / sesión vencida | 403 / 401; GET autorizado sigue disponible |
| Adjuntar real o corregir tipo en boleta 029 | cambia vista actual, conserva origen y evento; no permite tocar preexistente |
| Reversión sin cambios / con nuevo vínculo o edición | recupera estado previo / 409 sin borrar datos |
| Nuevo vínculo 029 | reduce saldo disponible de Tesorería y Tarjetas, no duplica crédito contable |

## Ejecución real posterior

La fase de implementación deberá producir un diagnóstico de solo lectura y una propuesta concreta para Sergio. Revisar las filas y diferencias; backup WC con CHECKSUM y RESTORE VERIFYONLY antes de migración y lote. Registrar evidencia fuera de Git. Solo después de revisión confirmar la selección exacta por la UI/API autorizada; no correr cargas por inferencia desde este plan.

Después de confirmar: SELECT de boletas/vínculos/eventos y saldo; diferencia del saldo debe ser exactamente la deuda agregada, con créditos preexistentes intactos. Segundo diagnóstico no propone esos pagos. Reversión únicamente de lote intacto; nunca restauración completa para deshacer una selección.

## Verificaciones efectivamente realizadas al planificar

- Leídos código actual, esquema WC de cuatro tablas y definición de vista mediante SELECT.
- Consultados seis saldos agregados de organismos; discrepancia Tapalqué incorporada a la spec.
- Revisión especializada de lógica financiera y de concurrencia.
- No ejecutados tests de aplicación, DDL ni cargas; no inspeccionado de nuevo el inventario físico de PDFs.

Decisión de implementación: la preparación viaja en el header X-Backfill-Preparacion al consultar respaldo; nunca en querystring, para no exponerla en logs de acceso. Código de mutaciones separado en escrituras.py y firmas/evidencia en respaldo.py, dentro del mismo módulo 029.
