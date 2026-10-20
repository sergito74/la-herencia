# NC0020-00120722 — corrección aplicada

Por autorización de Sergio20/10/2026, corregido documento2143515167 sin duplicar su crédito ni modificar pagos. Sigue Nota de Crédito/Pesos, con total fiscal **$16.252,67** (neto$13.431,96+IVA21%$2.820,71).

Activada marca Ajusta Tipo Cambio, vencimiento22/05/2025 según original y19renglones convertidos de cantidades físicas/precios negativos a cantidad1ARS/precios negativos financieros. Prorrateado neto fiscal por pesos de las líneas anteriores con mayores restos a centavos. Conservados IdDetalleCompra, producto, formulado, centro, rubro, destino y campaña de cada renglón. Se comprobó correspondencia de producto/centro/destino/campaña de los19renglones conFC0020-00401515/Id2143514876 y se agregó relación documental. Datos y líneas de esa factura intactos.

Verificados total fiscal a centavos, efectoUSD0 en cuenta bimonetaria y19renglones de costos que reducen neto$13.431,96 conUSD0 (cálculoABS(Pesos)*Signo, preservando signoNC). No son devoluciones de cantidades físicas. No se ejecutó FIFO ni cierre.

PDF `C:/Users/Sergio/Dropbox/Giamigli de Bolivar SA/Compras/04 2025 - 03 2026/20250522_BayaCasal.pdf`. Su observación y el portal indican diferencia$13.427,83, mientras el pie fiscal tiene$13.431,96: diferencia$4,13 conservada como discrepancia, prevalece fiscal. No se alteró para forzar coincidencia con el portal.

Respaldo verificado `WC_baya-nc120722-036_20261020_090116_061835.bak`. Script `backend/scripts/baya_casal_nc120722_036.py`; auditoría local `backups/baya-conciliacion-20261019/nc120722-correccion-*.json` con datos antes/después, importes por línea, origen, hash del PDF, costos, efectoUSD. Aplicación atómica con bloqueo, guardas de estado, no duplicación y lectura posterior a commit. No se escribieron datos ficticios para pruebas.
