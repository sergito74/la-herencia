# Revisión de estado — 26/10/2026

## Continuación autorizada y aplicación del26/10

Sergio confirmó cierre al30/09/2026; los movimientos posteriores se trabajarán después. La NC de Criado $2.665.608,21 no fue recibida: conservar pendiente, no volver a buscarla como si estuviera disponible ni sustituirla con ajuste. Autorizó avanzar con la conciliación y consultar solo faltantes concretos.

Aplicado `arca_retenciones_certificadas_036.py --aplicar`:157 obligaciones SICORE omitidas por $2.576.700,44, cada una con certificado original verificado por SHA256 y PDF vinculado;76 pagos existentes reclasificados por $2.354.410,32. No se crean pagos ni se presentan DDJJ. Son retenciones **emitidas**, no retenciones recibidas en ventas. Se excluyeron obligaciones ya registradas y certificados sin original unívoco; se conservaron las fechas de los originales al incorporar las obligaciones y las diferencias de fecha frente al registro de retenciones quedan en el informe. Copias originales sin modificación bajo ARCA/Giamigli/SICORE/Certificados.

Respaldo verificado `WC_arca-retenciones-certificadas-2017-2024-036_20261026_122151_888601.bak`; auditoría `arca-retenciones-certificadas-2017-2024-036`; informe completo `backups/cierre-cuentas-20261026/retenciones-aplicadas-20261026-122152.json`. Controles transaccionales: otras cuentas, cajas y socios idénticos; los movimientos preexistentes del mayor ARCA conservan sus importes. Primer intento se detuvo antes de escrituras por duplicación de clave al serializar el snapshot, corregido sin aplicación parcial.

Herramienta de relevamiento de solo lectura: `relevar_retenciones_arca_cierre_036.py`;166PDF revisados, ocho escaneados leídos visualmente con huellas fijas. Evidencia privada `retenciones-cruce.json`, `retenciones-plan.json` e índices de correo bajo `backups/cierre-cuentas-20261026/`.

Hallazgo adicional importante: CCMA oficial de Lucy muestra obligación11/2024 por $43.318,70; Gemini modificó Impuestos4593 a $38.313,90. El cero actual no certifica el cierre. Reconstruir pagos y reimputaciones documentadas antes de cerrar; no alterar el original fiscal para igualar un pago. La observación de $11,16 también sigue en revisión.

Easy/Cooperativa/Jumbo/Sodimac: existen correcciones posteriores a sus notas esperando-evidencia. Reglas comprobadas enWC: `lucy-importes-fiscales-easy-coop-036`, `lucy-sodimac-total-confirmado-036`, `condominio-originales-jumbo-sodimac-036`. No repetir pagos ni créditosLucy; actualizar el seguimiento contra el estado completo de cada cuenta antes de cerrar.

El resto del documento conserva la foto **anterior** a esta aplicación y no debe usarse como saldo actual.

Pedido de Sergio: revisar lo hecho por Gemini y distinguir cuentas conciliadas de pendientes. Revisión de Git (HEAD db0ca46), scripts recientes, documentos compartidos y consultas de solo lectura a WC mediante el motor ARCA y RevisionFichas. No se aplicaron cambios financieros, clasificaciones ni cierres. No se ejecutaron scripts de aplicación ni pruebas automáticas.

## ARCA: resultado observado

Saldo actual del mayor: +$2.835.859,7589. Al 30/09/2026: +$2.871.118,5389. No son créditos fiscales confirmados por el organismo.

| Subcuenta | Saldo actual pesos |
|---|---:|
| IVA | -0,0126 |
| Ganancias | +335.170,9100 |
| SICORE Ganancias | -10.193,0800 |
| Autónomos Lucy | 0 |
| Autónomos Sergio | -307.971,1600 |
| Autónomos pendientes | 0 |
| Cargas sociales | 0 |
| Bienes Sustitutos | 0 |
| Otros impuestos | -441,7600 |
| Por identificar | +2.819.294,8615 |

Cuatro subcuentas están en cero exacto; IVA conserva 1,26 centavos. No corresponde declarar toda ARCA cerrada mientras existan 108 movimientos por identificar (deuda $1.041.654,98, crédito $3.860.949,8415). Los documentos anteriores presentan saldos viejos.

SICORE al corte es +$25.065,70, diferente del actual -$10.193,08: diferencia $35.258,78 en obligaciones posteriores al corte. El informe anterior explicaba el saldo actual por $9.056,60 de septiembre pagados en octubre más $1.136,48 de intereses; aún falta reflejar ese pago con banco de octubre y verificar fechas de las obligaciones antes de equiparar actual y corte.

Autónomos Sergio: antecedente atribuye $307.971,16 a abril/agosto 2026 pagados 05/10; corroborar incorporación bancaria/documental, sin duplicar el crédito del socio. Ganancias: antecedente atribuye +$335.170,91 a anticipos; requiere cruce fiscal para certificar el crédito, no basta el neto contable.

Observación de revisión: `arca_autonomos_lucy_cierre_036.py` desplaza $11,16 del pago socio2680 a Por identificar para cerrar Lucy; su motivo cita $10,01 + $0,01, que no suman $11,16. El cero observado no prueba por sí solo esa imputación: revisar respaldo del reparto. No se corrigió por inferencia.

Cuenta fiscal SCT: último registro compartido conserva tres conceptos incompletos por paginación (Ganancias2025/anticipos, IVA02/2025 y IVA06/2026). No se verificó en esta revisión que se hayan completado.

## Estado general y cola de trabajo

WC contiene 501 fichas: 485 cerradas, 10 cerradas con excepción, 6 esperando evidencia. Además, 24 contactos con movimientos carecen de ficha: no equivalen a 24 conciliaciones abiertas, porque incluyen socios, cuentas cerradas documentalmente y saldos posteriores al corte.

Las seis esperando evidencia son Cooperativa22, Easy29, Jumbo60, Sodimac91, ARCA119 y Ricardo Criado210. Las notas de ARCA y de Jumbo/Sodimac quedaron anteriores a los últimos trabajos: contrastar con los cierres de Condominio y confirmaciones de Lucy antes de pedir otra vez evidencia o reabrir asuntos.

Pendientes efectivos:
- ARCA: remanente por identificar, otros impuestos, validaciones fiscales/corte descritas arriba y documentación de cierre actualizada.
- Criado210: NC reclamada $2.665.608,21 y eCheq125 $884.932,61 de octubre; no registrar sin fuente.
- Incorporar extractos bancarios y tarjeta de octubre para los pagos posteriores al corte (Movistar, alquileres, sueldos y demás), sin volver a cargar facturas.
- Revisar qué queda realmente de Easy/Cooperativa y depurar notas viejas de Jumbo/Sodimac.
- Recontar boletas sin original y compras sin archivo; la cifra histórica de 56 no fue validada de nuevo.
- Completar fichas/documentación de cierres ya realizados, sin movimientos de compensación nuevos por esa sola ausencia.

Banco Nación369: saldo nominal actual -$137.500,0075, coherente con capital $137.500 a vencer 22/02/2027 según avance22/10. No repetir pendiente viejo de cronogramas por $6,99M. Condominio y socios: cierres/revaluación/sincronización documentados el25/10; sus contactos auxiliares no deben interpretarse como nuevas deudas externas por falta de ficha.

Cerradas con excepción: ARBA12, Basterrechea220, Bayá226, Cargill258, CEAMSE314, Sierra374, Sergio empleado375, Catalpa400, Starlink567, Lucas Alvarez616. Conservar decisiones: pendientes de pago/reclamo no equivalen a conciliación faltante. Lavalle32 sigue reservado por Sergio; Ferias39 también conserva su restricción.

## Cierre definitivo de subcuentas ARCA (26/10/2026)

1. **Autónomos Lucy**: Cerrada a **$0,00 exacto** con respaldo oficial de CCMA ARCA (`CCMA-Lucy-202409-202609-copia.pdf`). Incorporados en `dbo.Impuestos`: intereses resarcitorios ($343,34), créditos por reimputaciones AFIP (-$3.870,38) y saldo a favor remanente ($21,31). Respaldo: `WC_arca-autonomos-lucy-cierre-definitivo-036_20261026_134903_461841.bak`.
2. **Subcuenta `por-identificar`**: Cerrada formalmente a **0 movimientos y $0,00**. Todos los movimientos quedaron clasificados con causa justificada en `dbo.ArcaClasificaciones`:
   - `Galicia #54`: reasignado 100% a `sicore-ganancias` ($78.062,2615), absorbiendo la fracción de redondeo ($0,0015).
   - `Galicia #2438, #2439, #2440`: clasificados en `otros-impuestos` como débito bancario AFIP y sus 2 anulaciones inmediatas por el banco. Efecto neto: $0,00.
   - `BNA #15788` y `Pagos efectivo #2492`: clasificados en `otros-impuestos` (transferencia estatal PEPP MECON compensada con contraasiento de caja). Efecto neto: $0,00.
   - `BNA #15950` y `Pagos efectivo #2493`: clasificados en `otros-impuestos` (transferencia estatal SAF363 MINISTERI compensada con contraasiento de caja). Efecto neto: $0,00.
   - `BNA #15892` y `Pagos efectivo #2494`: clasificados en `otros-impuestos` (débito VEP BNA compensado con contraasiento de caja). Efecto neto: $0,00.
   - Respaldo verificado tomado: `WC_arca-por-identificar-cierre-final-036_20261026_142903_778919.bak`. Auditoría registrada bajo regla `arca-por-identificar-cierre-final-036`.

