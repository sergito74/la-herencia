ORDENES SQL PACKAGE (COMPAT) — Aplica/Aplicar

Qué incluye
-----------
1) basPaqueteOrdenes.bas
   - Importador de .txt de consultas (igual que antes), pero ahora detecta automáticamente
     si el campo existe como [Aplica] o [Aplicar] y ajusta el SQL al vuelo.
   - Incluye un fix opcional para convertir TODAS las consultas existentes del archivo
     a un único nombre (el que realmente exista en tu BD).

2) Carpeta SQL con un ejemplo de consulta que usa el placeholder [[APLICA_CAMPO]].
   - Podés agregar tus .txt acá y, si no usan el placeholder, igual se normalizarán
     reemplazando [Aplica]<-> [Aplicar] según lo que tenga tu BD.

Cómo usar
---------
A) Parchear tus consultas actuales (sin importar nada):
   1. Importá el módulo basPaqueteOrdenes.bas a tu BD (Archivo > Importar > Archivos de texto > Módulo).
   2. Abrí el editor de VBA (ALT+F11) y ejecutá: Compat_AplicaAplicar_FixAll
      - Esto recorre todos los QueryDefs y estandariza [Aplica]/[Aplicar] al que exista.
   3. Listo.

B) Importar nuevas consultas desde .txt (igual que antes):
   1. Descomprimí este ZIP en alguna carpeta local.
   2. En Access, con el módulo importado, ejecutá: ImportarPaqueteOrdenes
   3. Elegí la carpeta "SQL" (o cualquier carpeta con tus .txt).
   4. El importador:
      - Si encuentra el placeholder [[APLICA_CAMPO]], lo sustituye por [Aplica] o [Aplicar] según tu BD.
      - Además, normaliza referencias existentes ([Aplica]↔[Aplicar]) por las dudas.
   5. Al final te muestra un informe de éxito/errores.

Notas
-----
- El módulo intenta detectar el campo en tablas típicas del proyecto (Ordenes_Detalles y Ordenes).
  Si no encuentra ninguna, asume [Aplica] por defecto.
- Si tu importador anterior se llamaba también ImportarPaqueteOrdenes, este módulo respeta ese nombre
  para que no cambies tu rutina.
- Si te aparece “Archivo no encontrado” al elegir carpeta, asegurate de que exista y que contenga .txt.
  Evitá rutas de red poco confiables y verificá permisos.

Soporte rápido
--------------
1) Ejecutar Compat_AplicaAplicar_FixAll si tus consultas ya están en la BD y fallan por el nombre del campo.
2) Usar ImportarPaqueteOrdenes para reinstalar desde .txt compatibles.
