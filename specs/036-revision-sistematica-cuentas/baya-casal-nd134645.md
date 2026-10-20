# Corrección ND0020-00134645

Aplicada en WC20/10/2026 por autorización expresa de Sergio. Se conserva IdDeuda2143517463 y los dos IdDetalleCompra2141381948/1949. No se crea otro documento ni se agregan pagos.

## Comportamiento corregido

- Tipo Factura→Nota de Débito; monedaPesos y TC1 conservados; Ajusta Tipo Cambio=true; vencimiento16/06/2026 según PDF.
- Dos líneas PROTERRA740 convertidas de cantidades físicas aproximadas4209,28 y2790,72kg a cantidad1/unidadARS, Ajuste financiero=true. Se conservan producto, IVA21%, rubro, centro, destinos9/8 y campaña2025/2026/Id24.
- Neto fiscal$294.839,93 repartido por proporción de los netos anteriores, mayores restos a centavos: **$177.294,83/$117.545,10**.
- Total de vista$356.756,3153, visible **$356.756,32** igual al fiscal; IVA redondeado$61.916,39. No se agregó un redondeo artificial.
- Relación documental con FC0020-00416539/Id2143515104, origen de la reprogramación RD136157 citada en la ND. Cabecera y líneas de factura original intactas; se agrega la relación simétrica que gestiona el repositorio.
- Verificados dos costos en vista de resultados, suma neta$294.839,93, dólares0; efecto de ND en cuenta bimonetariaUSD0. Conserva costos repartidos sin representar otra compra física de fertilizante.

## Evidencia y discrepancia

PDF original `C:/Users/Sergio/Dropbox/Giamigli de Bolivar SA/Compras/04 2026 - 03 2027/20260616_BayaCasal.pdf`: NOTA DE DEBITO, neto$294.839,93/IVA$61.916,39/total$356.756,32. El renglón explicativo y el portal usan diferencia$294.842,64 ($3.312.615,99−$3.017.773,35), es decir$2,71 por encima del neto fiscal. Se conserva el importe fiscal; discrepancia pendiente de explicar, sin ajustar el documento para imitar la observación del proveedor.

Respaldo verificado `WC_baya-nd134645-036_20261020_083957_772792.bak`; script `backend/scripts/baya_casal_nd134645_036.py`; auditoría local `backups/baya-conciliacion-20261019/nd134645-correccion-*.json` incluye antes/después, asignación, hash del PDF, costos y efectoUSD. Transacción con bloqueo, validación de neto/total/reparto/origen y lectura posterior a commit. Primer intento revertido íntegramente porque la guarda del origen comparaba también sus relaciones, que el repositorio actualiza simétricamente; corregida guarda para exigir intactos datos y líneas.
