# Verificación contra la planilla histórica (T027): 25/11/2026, primera pasada

**Fuente:** "Historico Negocio Ganadero (ver 2).xlsx", solapa "Negocio Ganadero La Herencia" (solo Bolívar, US$ con dólar billete).
**Sistema:** `GET /api/ganaderia/resultado?vista=campania&moneda=USD` (dólar de gestión: BNA comprador divisa, día hábil anterior).

| Rubro | Planilla 18/19 | Sistema 18/19 | Planilla 22/23 | Sistema 22/23 | Lectura |
|---|---|---|---|---|---|
| Ventas totales | 37.677 | 37.711 | 91.191 | 105.849 | 18/19: diferencia de TC. 22/23: el sistema suma Tapalqué (3 renglones), que la solapa no tiene. Falta el filtro por establecimiento |
| Vacunas | 2.270 | 2.285 | 2.417 | 2.457 | TC |
| Inseminación | 1.253 | 1.373 | 1.736 | 1.764 | 18/19 +120: a verificar con comprobante |
| Productos veterinarios | 494 | 499 | 1.388 | 1.495 | TC; 22/23 coincide con lo que encontró el forense |
| Aranceles vacunación | 369 | 374 | 125 | 307 | 22/23: cargas posteriores (forense) |
| Análisis laboratorio | 919 | 936 | 442 | 451 | TC |
| Honorarios profesionales | 704 | 716 | 751 | 770 | TC |
| Flete hacienda | 558 | 558 | 283 | 506 | 22/23: cargas posteriores |
| Amortización pasturas (fila "Avena" de la planilla) | 8.483 | 8.481 | 2.962 | 3.092 | coincide |
| Maíz diferido | 3.475 | 4.375 | 10.184 | 7.295 | la planilla es un valor manual ("Cultivos y forrajes") |
| Sorgo | 3.117 | 3.174 | 12.405 | 12.720 | ≈ |
| Maíz silo (fila "Maíz" de la planilla) | 2.608 | 5.021 | 7.960 | 13.971 | la planilla es un valor manual |
| Personal eventual | 248 | 248 | 0 | 0 | coincide |
| Gastos de administración | 976 | 985 | 199 | 391 | ahora es estructura |
| Movilidad | 81 | 81 | 158 | 172 | ahora es estructura |
| **Ha ganaderas** | 223,9 | 504,7 | 214,8 | 499,3 | **error del sistema:** la tabla Lotes mezcla lotes viejos y sus subdivisiones (suma 630 ha; el loteo vigente del plan 26/27 suma 402,1 ha), y antes de 2021/22 no hay Plan agrícola cargado. Se pregunta a Sergio |

**Rubros nuevos que la planilla no tenía:** personal permanente (70/20/10), mantenimiento de instalaciones y compra de hacienda (va aparte del costo).
