"""Atajo: permite ejecutar la guía de pruebas desde el servicio backend (carpeta de trabajo /app/asistente):

    docker compose run --rm backend python pruebas/probar_guia.py
"""

import runpy

runpy.run_path("/app/pruebas/probar_guia.py", run_name="__main__")
