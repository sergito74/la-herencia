# Research: 048 (revisado 06/11: vínculo desde Compras)

## R1. Documento de labor

- **Decision**: documento de un contacto con órdenes que tiene al menos un renglón de los rubros Fumigacion, Siembra, Cosecha, Fertilizacion, Disqueado o Embolsado Grano (91 facturas desde 2015).
- **Rationale**: Yanquelen también vende hacienda, semilla y urea; el primer listado incluyó "Vacas preñadas".

## R2. Dónde se vincula

- **Decision**: en el formulario de Compras, con un panel propio guardado por endpoints aparte (`GET/PUT /api/compras/{id}/ordenes-trabajo`), con el mismo patrón que "Documentos relacionados". En una compra nueva, el panel aparece después del primer guardado, igual que relacionados.
- **Rationale**: Sergio (06/11): "las facturas y NC/ND deben vincularse desde otro módulo; esta sección solo respeta esas vinculaciones". Se descartan las propuestas automáticas, la pantalla de revisión y los descartes.
- **Orden de la lista**: órdenes ejecutadas del contratista, primero las que no tienen factura y, dentro de eso, de la más nueva a la más vieja. Sin rótulos ni sugerencias.

## R3. Reparto

- **Decision**: al guardar el panel, se llama a `fijar_vinculos(id_compra, ids_orden, usuario)`: sincroniza `OrdenesContratistaFacturas`, y `motor.evaluar_contratista` → `guardar_corrida` → `aprobar_corrida(usuario)`. Sin órdenes, se guarda una corrida vacía que retira la imputación.
- **Neto repartible**: los renglones fuera de Semillas, Fertilizantes, Agroquimicos, Hacienda, Trabajos Maq. Propia y Gastos Comercializacion (verificar los nombres exactos en `dbo.Rubros`); en dólares, al TC del comprobante; la última fracción absorbe el redondeo.

## R4. NC/ND

- **Decision**: al agregar o quitar un relacionado en Compras, si la NC/ND queda relacionada con una factura con corrida aprobada, se imputa con las proporciones de la factura y su signo; si se quita, se retira. Si la factura cambia sus órdenes, se recalculan sus NC/ND.

## R5. Resultado sin doble conteo

- **Decision**: `costos_heredados` excluye, de las compras con corrida de contratista aprobada vigente, los renglones repartidos (todo lo que no está en los rubros excluidos). `costos_contratista` suma las fracciones aprobadas vigentes. `resultado.py` deja de leer `Ordenes_Trabajo_Contratista_Factura`.

## R6. Sin orden

- **Decision**: listado de facturas de labor sin vínculo (con renglones y la imputación manual) y aviso en el formulario al guardar una factura de labor sin órdenes. No bloquea, para no impedir registrar la deuda.
