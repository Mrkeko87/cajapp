import sqlite3
from flask import g, session, current_app
from flask_sqlalchemy import SQLAlchemy

# Instancia global de SQLAlchemy
db = SQLAlchemy()

# Modelo de Caja con SQLAlchemy
class Caja(db.Model):
    __tablename__ = 'cajas'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)

# Conexión SQLite manual (para otras tablas o conexiones dinámicas)
def get_db():
    if 'db' not in g:
        db_path = session.get('db_path')
        if not db_path:
            db_path = current_app.config.get('DEFAULT_DB_PATH', 'databases/default.db')
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Inicializador de base de datos para tablas con sqlite3
def init_db(filepath):
    conn = sqlite3.connect(filepath)
    cursor = conn.cursor()

    # Crear tabla de cajas (por si usas sqlite3 además de SQLAlchemy)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cajas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL
        )
    ''')

    # Crear tabla de objetos relacionada a cajas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS objetos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caja_id INTEGER NOT NULL,
            numero TEXT NOT NULL,
            FOREIGN KEY (caja_id) REFERENCES cajas (id)
        )
    ''')

    conn.commit()
    conn.close()

# Para control explícito de lo que puede importarse desde este módulo
__all__ = ['db', 'Caja', 'get_db', 'close_db', 'init_db']
