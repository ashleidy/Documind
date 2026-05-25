# app/utils/cleanup.py
import os
import shutil
import time

MAX_AGE = 1800  # 30 minutos en segundos

def cleanup_old_files(folder: str):
    """
    Borra archivos y carpetas más viejos de 30 minutos.
    Evita que el servidor se llene de PDFs y vectores viejos.
    """
    if not os.path.exists(folder):
        return

    now = time.time()

    for item in os.listdir(folder):
        path = os.path.join(folder, item)
        try:
            age = now - os.path.getmtime(path)
            if age > MAX_AGE:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.remove(path)
        except Exception:
            pass  # ignorar errores de archivos en uso