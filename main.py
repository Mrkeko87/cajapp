from db import conectar_postgres

conn = conectar_postgres()
cursor = conn.cursor()

# ejemplo simple
cursor.execute("SELECT NOW();")
resultado = cursor.fetchone()
print("Hora actual en PostgreSQL:", resultado)

conn.close()