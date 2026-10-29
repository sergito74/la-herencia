# Research: Detector de facturas faltantes

## R1. Ciclo de facturación
- **Decision**: mediana de las distancias (días) entre fechas de las últimas 12–24 facturas (sin NC, sin total 0 de particulares contadas igual como comprobante); se clasifica en mensual (30), bimestral (60) o trimestral (90) si la mediana cae a ±25% de alguno y al menos el 70% de las distancias están en ese rango; si no, sin ciclo. Mínimo 6 facturas en los últimos 24 meses.
- **Rationale**: robusto a una factura con fecha errónea; reproduce Coop. Eléctrica bimestral y Movistar mensual.
- **Alternatives**: contar meses calendario con factura (descartado: falsos de Estudio Criado y no detecta Movistar jun-2025).

## R2. Período facturado
- **Decision**: los períodos se generan como una secuencia de casilleros desde la primera factura analizada, cada uno de largo = ciclo; cada comprobante se asigna al casillero libre más cercano a su fecha (± medio ciclo); un casillero sin comprobante es un faltante. Esto evita que dos comprobantes en el mismo mes tapen un período (caso Movistar).
- **Alternatives**: leer el período del texto del renglón (no está en todos los proveedores).

## R3. Estados del período en curso
- **Decision**: fecha esperada = última factura + ciclo; margen 15 días (mensual) o 25 (bimestral/trimestral). Llegó / Pendiente (hoy ≤ esperada + margen) / Atrasada / ¿Baja? (3 ciclos sin factura, una sola pregunta, guardada).
- **Monto esperado**: mediana de las últimas 3 facturas; cambio de monto si |dif| > 30%.

## R4. Señales no recurrentes
- **Decision**: (a) pago sin vínculo a comprobante (vías de `vinculos.fuente`) y sin factura del proveedor de importe igual o suma de hasta 3 en ±60 días; (b) saldo a favor del proveedor con antigüedad > 90 días; (c) retención de Ganancias del proveedor sin comprobante de compra en ±30 días; (d) remito de compra sin factura vinculada con más de 60 días. Todas como "a verificar".
- **Rationale**: criterios de la auditoría 036 §7; ventana ±60 días como punto de partida (las ventanas no prohíben, solo avisan).

## R5. Exclusiones y alcance
- Ganadera San Justo excluida por nombre/CUIT; contactos de socios (375, 390, 549, 5670) y el contacto 0 excluidos; solo contactos con compras.
- Cuentas con resumen del proveedor: el detector solo avisa faltantes, no reimputa.

## R6. Integración 043
- **Decision**: el endpoint de resumen de la rutina 043 agrega, desde el día 5, la cantidad de facturas atrasadas del mes anterior con enlace al tablero.

## R7. Rendimiento
- **Decision**: lecturas en bloque (5 consultas), cálculo en memoria; cache por proceso de 10 minutos invalidada al guardar decisiones o marcas.
