# Relevamiento Bayá Casal (extranet) — 27/10/2026

Autorización: bóveda, portal 5, solo lectura (Sergio, 19-20/10/2026). Credencial: bóveda (nunca en archivos). Base previa: specs/036-revision-sistematica-cuentas/baya-casal-relevamiento-20261019.md.

## Ingreso
- `https://extranet.ebayacasal.com.ar/`, formulario `usuario` + `password` + botón submit; sin captcha ni segundo factor. Ingreso correcto lleva a `/home/`.

## Documentos
- Cuenta corriente bimonetaria `/ctacteA/`, formulario `form1` (oculto en acordeón): `desde` (date), `hasta`, `tipofecha` (`FV` vencimiento / `FC` emisión), `aplicaciones` (`NO`/`SI`). El conector lo completa por JS y lo envía: es solo el filtro de consulta.
- Columnas: Fec.Vto, Comprobante (`FC 0020 00465204`), Concepto, Fec.C.C., Tipo cambio, Imp $, Imp U$S, Saldo $, Saldo U$S, PDF.
- PDF: `obtenerPDF.php?file=<base64("CT;RI;6;74242;15/04/2026")>` devuelve HTML con `<embed src='data:application/pdf;base64,…'>`. Algunos (ej. RD) responden "No podemos encontrar el PDF"; esas filas se informan como error de descarga sin cortar la corrida.
- Tipos: FC factura, NC nota de crédito, ND nota de débito (Compras); RI recibo, CA aplicación, RG retención que hicimos en el pago (el enlace abre el recibo) → documentos sin carga.
- Número para Compras: `0020-00465204`. Archivos `AAAAMMDD_BayaCasal.pdf` en Compras del ejercicio.
- Si el comprobante ya tiene compra cargada con su archivo, se vincula a ese archivo y no se guarda otra copia (el PDF del portal no es idéntico byte a byte al guardado a mano).

## Estado de cuenta
- Misma pantalla desde 01/01/2010 sin aplicaciones; último saldo $ y U$S (positivo = le debemos). 27/10/2026: US$ 2.055,85 y $ 0,00 (coincide con el relevamiento del 19/10).
- Fotos informativas (no se compara saldo): la deuda con Bayá incluye compras firmes no facturadas que el portal no muestra (ver 036).

## Prohibido (constancia de revisión)
Solo navega, aplica el filtro de consulta y descarga. No usa "Cambiar contraseña", mensajes, "Cambiar empresa/rubro" ni ningún formulario distinto del ingreso y el filtro.

## Primera corrida (27/10/2026)
20 documentos del ejercicio: 9 comprobantes ya cargados en Compras (vinculados a su compra y archivo), 11 recibos/aplicaciones nuevos guardados en Compras.
