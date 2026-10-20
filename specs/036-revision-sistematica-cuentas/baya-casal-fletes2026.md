# Fletes enero2026 — corrección e imputación

Sergio definió explícitamente: costos reales convertidos aUSD para resultados del cultivo, pero documentos y pago exclusivamente en subcuenta pesos del proveedor. Aplicado20/10/2026 con respaldo, sin duplicar facturas/bancos/retención.

| Documento | IdDeuda | Neto pesos | Total fiscal pesos |
|---|---:|---:|---:|
| FC437731,02/01/2026 | 2143515345 | 280.100,00 | 338.921,00 |
| FC438310,07/01/2026 | 2143515343 | 640.393,00 | 774.875,53 |

Se ajustaron mínimamente precios unitarios para reproducir netos fiscales, prorrata del reparto anterior y mayores restos a centavos. Conservadas cantidades/unidades, productos, centros, rubros, destinos, campañas, IVA21 y naturaleza no financiera. Vencimientos01/02 y06/02 según PDFs. No se activó Ajusta Tipo Cambio, porque anularía indebidamente el costo económicoUSD.

El coeficienteIVA de las dos vistas de totales se evalúa en precisión doble para estas dos facturas exclusivamente, agregando su Id al caso de precisión ya existente. Esto evita los$0,02 de deriva porIVA SQL REAL enFC438310 y permite respetar a la vez neto y total fiscal. Definiciones antes/después en auditoría; los totales de los documentos financieros existentes se compararon sin cambios. No se agregó un gasto ficticio ni una línea de redondeo.

## Cancelación documental

Galicia3034,04/02/2026, transferenciaLR24GE9610:$1.111.663,22. Retención222/certificado2026-1:$2.133,31. Total$1.113.796,53 idéntico al fiscal. Respaldos: PDFs de ambas facturas, transferencia y certificado enviados aSusana04/02; portalRI70854 dice PESOS y cancela el grupo.

Imputaciones previas15696/15697 asignaban pagoGalicia2682 de17/07/2025 a estos fletes de2026;15700/15737 asignaban pago3034 yret222 aFC431429, fertilizante. Anuladas lógicamente solo esas cuatro aplicaciones, con motivo/usuario/fecha, y creadas tres aplicaciones manuales:

- Galicia3034 → FC437731:$338.921,00.
- Galicia3034 → FC438310:$772.742,22.
- Retención222 → FC438310:$2.133,31.

Ambas facturas quedan cubiertas exactamente; banco y certificado nominales intactos. Galicia2682 conserva sus demás aplicaciones. Quedan liberados$1.113.796,55 de su imputación errónea anterior para revisar luego contra comprobantes del pago2025; no reasignados por inferencia. Tampoco se fuerza una nueva cancelación deFC431429 al retirar aplicaciones indebidas.

## Separación de costo y cuenta corriente

Cuatro entradas en mecanismo existente ValuacionProveedor, conUSD0: Compras2143515345/2143515343, Galicia3034 yRetenciones222. Evitan conversión ficticia aUSD en cuenta, sin afectar compras ni vistas de costos. Verificado grupo: saldoPesos0 ysaldoUSD0.

Vista de costos conserva11renglones y costo neto$920.493,00, convertido con criterio vigente BNA de cada factura: **USD632,41** agregado (incluye la porción originalmente enNoAplica, que no se asignó a cultivo por conjetura). No se duplicó como otro gasto. Todas las líneas mantienen dólares positivos y su distribución previa.

Respaldo verificado `WC_baya-fletes2026-036_20261020_093458_563800.bak`. Script `backend/scripts/baya_casal_fletes2026_036.py`; auditoría `backups/baya-conciliacion-20261019/fletes2026-correccion-*.json` conserva estados originales, aplicaciones/valuaciones, reparto, vistas, costos y verificación bimonetaria. Transacción con bloqueo y guardas, lectura posterior alcommit; noFIFO global ni cierre.
