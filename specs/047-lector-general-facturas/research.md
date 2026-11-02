# Research: Lector general

## R1. Fuente de datos

- **Decision**: texto del PDF como fuente principal, más el enlace del QR de ARCA cuando el PDF lo traiga como vínculo. Los dos deben coincidir.
- **Rationale**: el equipo no tiene decodificador de imágenes QR y las reglas piden no instalar dependencias sin pedido. Los QR solo como imagen no se leen en esta etapa: rige el texto y la validación al centavo.
- **Alternatives**: agregar un decodificador de imagen. Se reconsidera si la simulación muestra que aporta cobertura; requiere autorización.

## R2. Reuso de carga

- **Decision**: exponer el lector general como un conector que devuelve `DatosCompra` y cargar con `boveda.carga.cargar`.
- **Rationale**: ya valida cierre al centavo y duplicados, y es el circuito de Agrovet/Movistar.

## R3. Imputación

- **Decision**: últimas 3 compras del proveedor por fecha; deben coincidir rubro, centro, destino y campaña en todas sus líneas. La campaña solo se copia si es "No Aplica" o sigue vigente a la fecha del comprobante; si no, queda a mano.
- **Rationale**: decisión de Sergio (FR-007); evita arrastrar una campaña vencida (auditoría de campañas 036).

## R4. Una línea por comprobante

- **Decision**: una sola línea por alícuota con la imputación común, con la descripción "Según factura".
- **Rationale**: los productos no se leen de forma genérica. Stock: los proveedores cuyas compras mueven stock quedan fuera y van a mano.

## R5. Revisión

- **Decision**: reusar `cargado_solo` y `para_cargar`, que ya quedan pendientes hasta `Revisado`. Verificar que el flujo de carpetas también lo haga.
- **Rationale**: FR-009 sin mecanismo nuevo. Los `ya_estaba` no son documentos nuevos cargados y siguen su regla.

## R6. Activación

- **Decision**: apagado por defecto; se enciende tras aprobar el informe de simulación.
- **Rationale**: SC-001 y regla "no romper saldos".
