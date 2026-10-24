# Revisión de los 18 pagos restantes — 24/10/2026

## Dos enlaces corregidos (aplicado)
Compras2143509653/pago375 y2143510007/pago568 ahora apuntan a los originales correctos22/01/2013 y04/04/2014. Solo Documento Original modificado; marca SSMA_TimeStamp automática. Respaldo verificado WC_condominio_enlaces_pdf_036_20261024_113454_343539.bak en la carpeta central de SQL Server. Snapshot backups/condominio-15-medios-036/enlaces-pdf-20261024-113455.json. Control de saldos de todos los contactos, cajas y socios idéntico. Repetición devuelve ya_aplicado_sin_escrituras. Primer intento revertido íntegro por comparar también la marca automática de versión; original persistido comprobado antes de reintentar. Access intacto.

## Nueva evidencia bancaria y fiscal (solo análisis)
La búsqueda anterior exigía importe exacto y por eso no detectaba cobros que el ticket desglosa con uno o dos centavos de diferencia respecto de su total fiscal. Se agregó exploración opcional --explorar-centavos (hasta0,03), informe separado; una cercanía de importe nunca adquiere estado confirmado por esa búsqueda. No modifica el informe exacto ni se usa para aplicar correcciones automáticas.

De los18:10 originales dicen Visa débito y el importe cobrado por esa vía coincide exactamente con un único débito HSBC del comercio y fecha cercana. Se revisaron visualmente total, cobro y vuelto/resto del ticket. Los10 suman2130,55 en pagosWC y2130,51 en banco (diferencia neta-0,04). No convertir automáticamente todo el total fiscal en débito: algunos tickets muestran Su pago por centavos y otros un vuelto. No se crearon pagos ni se alteraron importes, medios, aplicaciones, caja o socios en este tramo de análisis. La representación única debe conservar el importe fiscal y el banco reales sin registrar el mismo gasto dos veces ni inventar un aporte por centavos.

| Pago | Total fiscal / pago WC | Visa débito y banco | Diferencia banco menos total | Detalle del ticket |
|---|---:|---:|---:|---|
| 516 | 183.99 | 184.00 | +0.01 | Vuelto0,01 |
| 562 | 178.91 | 178.92 | +0.01 | Vuelto0,01 |
| 604 | 255.51 | 255.52 | +0.01 | Vuelto0,01 |
| 611 | 173.72 | 173.73 | +0.01 | Vuelto0,01 |
| 625 | 194.19 | 194.18 | -0.01 | Su pago0.01 |
| 715 | 230.13 | 230.12 | -0.01 | Su pago0.01 |
| 725 | 202.54 | 202.53 | -0.01 | Su pago0.01 |
| 733 | 200.80 | 200.78 | -0.02 | Su pago0.02 |
| 739 | 280.74 | 280.73 | -0.01 | Su pago0.01 |
| 752 | 230.02 | 230.00 | -0.02 | Su pago0.02 |

Fuentes bancarias (PDF, página, hash, operación y fecha) y comprobantes: backups/condominio-15-medios-036/diez-debitos-centavos-revision.json, puentes-68-hsbc-explorar-centavos.json; originales y hashes en destinatarios/revision.json. Galerías de revisión pendientes1–5 y cobros1–3, no agregadas a Git.

Otros5 candidatos14,40,362,530,660: cercanía bancaria de0,01–0,02 pero los originales dicen Efectivo; contradicción explícita. No alcanza para confirmar débito ni origen de caja. Pago14 además está a nombre de Sucesión, no Giamigli. Mantener pendiente.

Restantes3 pagos177,331,360: originales dicen Efectivo, sin candidato bancario bajo este criterio. Falta acreditar procedencia/reintegro y representación de socio; no generar un aporte porque no aparezca banco.

Los18 siguen sin reclasificación aplicada; ahora10 tienen prueba concordante de débito con detalle de centavos,5 contradicción y3 efectivo sin origen acreditado. Las6 excepciones de destinatario (13,14,15,16,18,75) siguen sin justificación económica; no trasladar automáticamente a socios. No declarar conciliación cerrada.


### Diez débitos aplicados — 24/10
Auditoría137 con respaldo:10 pagos vigentes de total fiscal2130,55 a banco exacto2130,51/medio10;10 componentes no bancarios documentados (vuelto/complemento),20 filas compensatorias de caja anuladas. Todos los saldos de contactos/cajas/socios idénticos; no nuevos pagos/gastos ni aportes. 68=59débitos+1tarjetaLucy+8pendientes. Detalle individual, respaldo y controles en [condominio-diez-centavos-aplicados-20261024.md](condominio-diez-centavos-aplicados-20261024.md).
