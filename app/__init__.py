# app/__init__.py
from flask import Flask
from flask_cors import CORS
from config import Config
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)

    # Carpetas necesarias
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['CHROMA_PATH'],   exist_ok=True)

    # Rutas
    from app.routes import main
    app.register_blueprint(main)

    # Worker — solo en proceso principal
    import os as _os
    is_main = (
        not app.debug or
        _os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    )
    if is_main:
        from app.utils.queue import start_worker
        start_worker()

    return app