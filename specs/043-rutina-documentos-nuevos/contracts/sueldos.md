# Sueldos recibidos por mail — 29/10/2026

Entrada: PDF propio de Giamigli (CUIT 30712114602) con SUELDO NETO + encabezado C.U.I.T. EMPRESA, o Resumen de Sueldos. Se intercepta antes del clasificador comercial. No cambia la lectura de otros adjuntos.

Paquete: 1–50 páginas, un recibo mensual por página, mismo período. Cada página identifica empleador y CUIL; cada CUIL debe resolver a un solo contacto Empleado. Solo se aceptan códigos de concepto conocidos y signos esperados. Aportes patronales y costo total empleador no se cargan como haberes ni deducciones del empleado. Haberes menos descuentos = neto impreso al centavo.

Persistencia: dbo.Remuneraciones, columnas monetarias existentes, deducciones positivas. Sin pagos ni contactos nuevos. En ausencia de fecha impresa se usa fin del período (convención del importador existente), expresamente como devengamiento. Se serializa comprobación/inserción junto con el aviso. No se duplica empleado+período normalizado, aun si cambia el PDF; una diferencia con liquidación existente detiene la carga sin reemplazarla.

Archivos: paquete y resumen originales bajo Personal/Recibos/año; una página por empleado bajo nombre estándar de 028. No se sobrescribe un individual distinto. Se verifica contenido económico si el archivo ya existe. Si SQL se revierte tras crear archivos, estos quedan recuperables y se verifican al reintentar.

Avisos: tipo recibos_sueldo, módulo tesoreria, estado cargado_solo si insertó al menos una liquidación, ya_estaba si todas existían; enlace a /personal/remuneraciones. Un aviso por paquete/SHA. Resumen: referencia, sin generar deuda ni un segundo aviso de carga. Errores usan la preservación y aviso pendiente existentes de 043. Recuperación del mail omitido con script de simulación/aplicación, respaldo verificado antes de escrituras; no se retroceden marcas.

Verificaciones: [validacion-sueldos-20261029.md](../validacion-sueldos-20261029.md).
