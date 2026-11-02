# Data Model

Sin tablas nuevas de negocio.

- **Comprobante leído** (en memoria): cuit emisor, cuit receptor, tipo, letra, número, fecha, moneda, TC, netos por alícuota, IVA por alícuota, percepciones, no gravado, total, CAE.
  Validación: suma de componentes = total exacto; CUIT emisor con contacto; CAE presente.
- **Imputación habitual** (en memoria): rubro, centro, destino, campaña; surge de las últimas 3 compras.
- **Rutina_Programacion**: agrega `LectorGeneralActivo` bit, por defecto 0 (migración con backup verificado).
- **DocumentosNuevos**: sin cambios; `Estado`, `Motivo`, `IdRegistro` y `Revisado` cubren el ciclo.

Estados: documento nuevo → `cargado_solo` o `para_cargar` → revisado.
