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

No se ejecutan transferencias, emiten cheques ni calculan alícuotas fiscales. Los medios son previsiones; retenciones previstas se indican en observaciones hasta contar con comprobantes y soporte de aplicación. Documentos en otra moneda requieren conciliación documentada desde Cuentas Corrientes; nunca se pesifican silenciosamente. Estos límites se muestran en la pantalla.

Errores 404 inexistente, 409 conflicto de estado/saldos, 422 solicitud inválida. Sin pruebas que escriban producción.
