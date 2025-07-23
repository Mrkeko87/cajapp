import os
from flask import Flask, session

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'clave-secreta'
    app.config['DEFAULT_DB_PATH'] = 'databases/default.db'  # Base por defecto

    # Registrar el context processor dentro de create_app
    @app.context_processor
    def inject_db_name():
        db_path = session.get('db_path', app.config['DEFAULT_DB_PATH'])
        db_name = os.path.basename(db_path).upper()
        return dict(db_name=db_name)

    # Importar y registrar blueprint
    from .routes import bp
    app.register_blueprint(bp)

    # Registrar cierre de DB (si tienes close_db en models.py)
    from .models import close_db
    app.teardown_appcontext(close_db)

    return app
