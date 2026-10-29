# Sueldos octubre — validación y seguimiento, 29/10/2026

Pedido: revisar barrido y cargar octubre faltante. Sergio confirmó avanzar y consultó ubicación y separación de los PDF; se le indicó Personal/Recibos/2026, uno por empleado, conservando paquete completo y resumen.

Fuente: Outlook, mail del estudio recibido 28/10/2026 21:12:17, asunto GIAMIGLI DE BOLIVAR SA - Sueldos 10/2026. Lectura COM sin mover/marcar/enviar. Copia original en `C:/dev/LaHerencia/backups/sueldos-octubre-20261029/`, adjuntos RECIBOS OCT26.pdf y RESUMEN OCT26.pdf. Verificados visualmente los dos recibos y resumen (imágenes en esa carpeta). Sin conflictos con trabajo de la otra sesión en scripts/036 y planilla de revisión: preservados.

Causa: corrida 8 del 29/10/2026 08:22–08:39 avanzó marca Outlook a 29/10 08:12:32; ambos documentos no reconocidos por el clasificador, ignorados sin aviso. No había liquidaciones Octubre 2026 ni documentos de sueldos registrados. El importador histórico solo procesa archivos individuales ya guardados y no estaba conectado al barrido.

Lectura nueva: Marcelo Sierra (374, CUIL 20132391670), neto 1396407.00 incluyendo Día Gremio 40880.22; Sergio Giamberardini (375 empleado, CUIL 23238598109), neto 1800000.00. Total 3196407.00, coincide con resumen. No confundir Sergio empleado con cuenta socio. Fecha de cierre 31/10/2026 como devengamiento según convención anterior: no se acredita ni se crea pago. Sergio informado en chat.

Pruebas: `pytest tests/documentos_nuevos -q` → 56 pasan. Sin escrituras en WC: netos y conceptos/signos desconocidos, otro empleador, dos páginas reales con repositorio simulado, separación por CUIL, reintento sin duplicación y diferencia en liquidación existente. Advertencias previas de FastAPI/Starlette. No se instalaron dependencias.

Aplicación pendiente. Script simula por defecto; --aplicar toma respaldo verificado y carga/aviso en transacción. Las copias PDF creadas antes de una eventual reversión SQL se pueden reutilizar tras validar identidad/período/importes; nunca pisa archivos distintos.


## Aplicación y resultado

Aplicado `python -m scripts.reprocesar_sueldos_mail <EntryID del mensaje> --aplicar` el 29/10/2026, sin alterar marcas del barrido ni leer otros mensajes. Respaldo COPY_ONLY/CHECKSUM y RESTORE VERIFYONLY satisfactorios:
`C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\Backup\WC_sueldos-mail-octubre-20261029_20261029_111526_090502.bak`.

- IdSalario 1829633338: contacto 374 Marcelo Sierra, Octubre 2026, neto 1396407.00.
- IdSalario 1829633339: contacto 375 Sergio empleado, Octubre 2026, neto 1800000.00.
- Un registro por empleado/período; fecha de devengamiento 31/10/2026. Sin registros de pagos.
- DocumentosNuevos 51: resumen guardado como referencia, sin nuevo gasto. Documento 52: paquete de recibos cargado, aviso pendiente de revisión con enlace a `/personal/remuneraciones`.
- Archivos finales en `C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Personal\Recibos\2026`: `2026 10 Marcelo Sierra.pdf` y `2026 10 Sergio Giamberardini.pdf` (una página cada uno), `2026 10 Recibos completos.pdf` (original de dos páginas) y `2026 10 Resumen sueldos.pdf` (original del estudio).
- Se reabrieron los PDF individuales, se comprobó CUIL y neto por página y se revisaron renders: páginas completas, sin cortes ni pérdida visual. Imágenes `*-individual.png` en backups/sueldos-octubre-20261029, fuera de Git.
- Se invocó el endpoint de apertura de recibo para ambos IdSalario: resuelve a cada PDF individual correcto.
- Compilación de módulo y script sin errores y `git diff --check` limpio. No se modificaron datos fuera de WC ni archivos Access, no se enviaron ni marcaron correos.
- Al finalizar no había corridas activas y la aplicación estaba cerrada (sin puerto 8000 ni pids.json del lanzador). No se levantó un servidor aislado: la próxima apertura usa el lector integrado automáticamente. No hay pasos manuales de carga pendientes.

Alcance del formato probado: recibo mensual nuevo del estudio con un empleado por página y conceptos reconocidos. Otros códigos/formatos quedan para revisión con el archivo preservado. El sistema no deduce pagos a partir del resumen.
