"""Importa extractos bancarios nuevos (BNA y Galicia) con detección de duplicados robusta.

La lógica vive en `src.features.tesoreria.extractos_pdf` (la usa también la pantalla de Tesorería para subir el PDF).
Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.importar_extractos [--aplicar]
"""

import sys

from src.features.tesoreria.extractos_pdf import main

if __name__ == "__main__":
    main(aplicar="--aplicar" in sys.argv)
