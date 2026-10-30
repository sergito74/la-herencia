# Contrato 046

Ruta canónica `/finanzas/ordenes-pago`; `/finanzas/recibos-pagos` redirige allí.
API `/api/ordenes-pago`, sesión requerida; escrituras solo Administrador.

- GET `/`: filtros proveedor/estado, paginación 50 (máximo 100).
- GET `/facturas?idContacto=`: compras en pesos, no suspendidas, saldo unificado al centavo; incluye reservas de otras OP emitidas. No aplica conversiones nuevas a documentos en dólares.
- POST `/`, PATCH `/{id}`: proveedor, fecha, fechaPago, observaciones, facturas (idCompra/importe), medios previstos (medio/cuenta/importe). Solo se edita Borrador. Facturas únicas, mismo proveedor; sumas de medios y facturas iguales. Moneda ARS explícita.
- POST `/{id}/emitir`, `/{id}/anular`: revalidación transaccional. Emitida reserva importe; Anulada libera reserva. No genera movimiento ni deuda. Pagada no se anula desde aquí.
- GET `/{id}`: cabecera, detalle y medios.
- GET `/recibos`: bandeja paginada, proveedor opcional; pendientes e históricos.
- GET `/recibos/{id}/pdf`: archivo registrado, PDF existente con hash verificado, nunca ruta arbitraria.
- GET `/movimientos?idContacto=`: egresos reales del proveedor, importes disponibles.
- POST `/recibos/{id}/vincular`: datos del recibo confirmados (proveedor, fecha, número, total ARS), OP opcional y aplicaciones explícitas (origenMovimiento/idMovimiento/idCompra/importe). Valida mismo proveedor, signo, capacidad de movimiento, saldo de factura, total del recibo y correspondencia exacta con OP. Repetir no duplica. Conserva PDF/hash y las aplicaciones en una transacción; revisa aviso solo al terminar.

- POST/PATCH de la OP aceptan además `retenciones[]` (la propuesta confirmada: codRegimen, concepto, basePago, pagosAnteriores, retencionesAnteriores, alicuota, noSujeto, retencion, simulador). Se valida que la suma de los medios = facturas − retención. GET `/{id}` devuelve `retencionGanancias` y `retenciones`.
- POST `/recibos/{id}/vincular` acepta además `retencion`, `certificadoRetencion` y `anticipo`:
  - aplicaciones + retención + anticipo = total del recibo;
  - con OP, la retención tiene que ser la de la OP y los pagos tienen que sumar el neto;
  - sin OP, si hay retención se pide el certificado;
  - las aplicaciones pueden ir vacías solo si hay anticipo.

## Retenciones de Ganancias RG 830 (historias 4 y 5)
- POST `/retenciones/proponer` {idContacto, fechaPago, facturas[{idCompra, importe}], excluirOrden?} → {condicion{retiene, motivo?, aviso?, inscripto?, padronAl?}, lineas[], total, avisos[]}. Solo lectura. Consulta el simulador público de ARCA y suma los pagos del mes en OP emitidas o pagadas del mismo proveedor y régimen.
- GET `/retenciones/regimenes`: regímenes de ARCA para inscriptos (código, concepto, alícuota, no sujeto).
- GET `/retenciones/rubros` y PUT `/retenciones/rubros/{idRubro}` {codRegimen|null, estado Borrador|Validado contador|Ratificado estudio, observaciones}. PUT solo Administrador.
- GET `/retenciones/exclusiones` (filtro opcional por idContacto) y POST {idContacto, desde, hasta, observaciones}: 422 si `hasta` < `desde`. DELETE `/retenciones/exclusiones/{id}`. Escrituras solo Administrador.
- POST `/retenciones/padron`: descarga el padrón público de ARCA y actualiza los CUIT de los contactos. Solo Administrador.
- GET `/{id}/mail-estudio`: `.eml` con `X-Unsent: 1`, para administracion@estudiocriado.com con copia a rcriado@, y las facturas adjuntas. El sistema no envía nada.

No se ejecutan transferencias ni se emiten cheques. La retención de Ganancias RG 830 es una propuesta calculada con el simulador público de ARCA que confirma el usuario; el certificado lo emite el estudio contable. Las OP admiten solo facturas en pesos; los documentos en otra moneda se concilian desde Cuentas Corrientes y nunca se pesifican silenciosamente.

Errores 404 inexistente, 409 conflicto de estado/saldos, 422 solicitud inválida, 503 simulador o padrón de ARCA sin respuesta. Sin pruebas que escriban producción.
