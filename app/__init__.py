import os
from flask import Flask, session

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'clave-secreta'
    app.config['DEFAULT_DB_PATH'] = 'databases/trastero.db'  # Base por defecto

    # Configuración SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.getcwd(), app.config['DEFAULT_DB_PATH'])
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Importar e inicializar SQLAlchemy
    from .models import db, close_db
    db.init_app(app)  # <-- Aquí inicializas SQLAlchemy con la app

    # Registrar el context processor dentro de create_app
    @app.context_processor
    def inject_db_name():
        db_path = session.get('db_path', app.config['DEFAULT_DB_PATH'])
        db_name = os.path.basename(db_path).upper()
        return dict(db_name=db_name)

    # Importar y registrar blueprint
    from .routes import bp
    app.register_blueprint(bp)

    # Registrar cierre de DB (close_db)
    app.teardown_appcontext(close_db)

    return app
