# Tabla rubro → destino (propuesta 14/11/2026)

Incluye los 48 rubros usados en compras desde el 01/07/2025 (n = renglones), con el destino que propongo para cada uno. "Depende" quiere decir que la regla se resuelve renglón a renglón; si no se puede, va a la lista.

## A cultivo — insumos (entran a stock y se imputan al usarse)

| Rubro | n | Parte |
|---|---|---|
| Herbicidas | 239 | Agroquímicos |
| Coadyuvantes | 127 | Agroquímicos |
| Insecticidas | 23 | Agroquímicos |
| Fungicidas | 10 | Agroquímicos |
| Fertilizantes | 49 | Fertilizantes |
| Semillas | 28 | Semilla |
| Inoculantes | 4 | Semilla |

## A cultivo — de una sola vez

| Rubro | n | Parte |
|---|---|---|
| Fumigacion | 22 | Labores |
| Siembra | 11 | Labores |
| Fertilizacion | 5 | Labores |
| Disqueado | 4 | Labores |
| Cosecha | 5 | Cosecha |
| Control Cosecha | 5 | Cosecha |
| Seguimiento cultivos | 93 | Asesoramiento/análisis |
| Analisis PG | 2 | Asesoramiento/análisis |
| Seguros Agricolas | 17 | Seguro agrícola |
| Flete insumos | 13 | Fletes |
| Gastos Comercializacion | 24 | Comercialización |
| Flete granos | 3 | Comercialización |
| Extraccion Grano | 1 | Comercialización |
| Honorarios Laboratorio | 2 | Comercialización (calidad del grano) |

## Depende

| Rubro | n | Regla |
|---|---|---|
| Analisis laboratorio | 2 | De suelo → Asesoramiento del cultivo; de hacienda → Ganadería |
| Combustible | 16 | Con orden de labor propia → Labores del cultivo; si no → Estructura |
| Financiamiento | 17 | Si es de un insumo (canje, plazo) → cultivo de ese insumo; si no → Financiero |
| Insumos productivos | 4 | Entra a stock. Lo imputa la orden de embolsado/enrollado según lo guardado: grano para vender → Comercialización del cultivo; forraje → cultivo forrajero; grano para consumo propio → Ganadería |

## Ganadería

Productos Veterinarios (29), Vacunas (15), Inseminacion (5), Aranceles Vacunacion (5), Flete hacienda (3).

## Financiero

Gastos bancarios (36).

## Estructura

- **Servicios**: Electricidad (131), Internet (27), Telefono (22), Gas (17).
- **Seguros**: Seguros Laborales (103), Seguros Generales (83).
- **Mantenimiento y herramientas**: Mantenimiento Construcciones (96), Mantenimiento Maquinarias (29), Mantenimiento Instalaciones (13), Herramientas (6).
- **Honorarios y administración**: Gastos de Administracion (21), Honorarios Contables (19), Honorarios Administracion (16), Honorarios Profesionales (10).
- **Movilidad y viáticos**: Viaticos (428), Movilidad (8).
- **Otros**: Insumos Generales (16), Bienes de uso (5, se amortiza aparte).

## Observaciones (corregido 14/11)

- **Flete granos** queda en Comercialización, como hoy.
- **Arrendamiento** es un ingreso, no un costo. Sale de la estructura de costos.
- **Silobolsa, hilo y malla**: su destino depende de lo que se guarda, y lo resuelve la orden que los usa.
- **Analisis laboratorio** pasa de "Otro" a Depende.
