import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app


import qrcode, unicodedata
import shutil
from PIL import Image, ImageDraw, ImageFont
from app.models import Caja, get_db



bp = Blueprint('main', __name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FOLDER = os.path.abspath(os.path.join(BASE_DIR, '..', 'databases'))



import pathlib
pathlib.Path(DB_FOLDER).mkdir(exist_ok=True)  # crea carpeta si no existe

@bp.route('/seleccionar_db', methods=['GET', 'POST'])
def seleccionar_db():
    if request.method == 'POST':
        # Subir archivo .db
        if 'db_file' in request.files and request.files['db_file'].filename != '':
            file = request.files['db_file']
            if file.filename.endswith('.db'):
                filepath = os.path.join(DB_FOLDER, file.filename)
                file.save(filepath)
                session['db_path'] = filepath
                flash('Base de datos cargada correctamente.', 'success')
                return redirect(url_for('main.index'))
            else:
                flash('Solo archivos con extensión .db permitidos.', 'error')

        # Seleccionar o crear base existente o nueva
        elif 'db_name' in request.form:
            nuevo_nombre = request.form['db_name']
            if not nuevo_nombre.endswith('.db'):
                nuevo_nombre += '.db'
            filepath = os.path.join(DB_FOLDER, nuevo_nombre)
            if os.path.exists(filepath):
                # Solo cambiar la base activa en sesión
                session['db_path'] = filepath
                flash(f'Se seleccionó la base de datos: {nuevo_nombre}', 'success')
                return redirect(url_for('main.index'))
            else:
                # Crear base nueva
                from .models import init_db
                init_db(filepath)
                session['db_path'] = filepath
                flash(f'Base de datos {nuevo_nombre} creada y seleccionada.', 'success')
                return redirect(url_for('main.index'))

        else:
            flash('Selecciona o crea una base de datos.', 'error')

    # Listar bases de datos en carpeta
    dbs = [f for f in os.listdir(DB_FOLDER) if f.endswith('.db')]
    return render_template('seleccionar_db.html', dbs=dbs)

@bp.route('/')
def index():
    db_path = session.get('db_path')
    if not db_path:
        return redirect(url_for('main.seleccionar_db'))
    
    db_name = os.path.basename(db_path).upper()
    return render_template('index.html', db_name=db_name)


def generar_qr_con_id(id_caja, carpeta_qr):
    # Generar QR
    qr = qrcode.QRCode(version=1, box_size=12, border=4)
    qr.add_data(str(id_caja))
    qr.make(fit=True)
    img_qr = qr.make_image(fill='black', back_color='white').convert('RGB')

    # Texto grande debajo del QR
    try:
        # Windows: cambia esta ruta si usas otro sistema
        font_path = "C:\\Windows\\Fonts\\arialbd.ttf"
        font_size = 100  # muy grande
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()

    text = f"ID: {id_caja}"
    draw_temp = ImageDraw.Draw(img_qr)
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Crear imagen final (QR + espacio para texto)
    qr_width, qr_height = img_qr.size
    total_height = qr_height + text_height + 40
    img_final = Image.new("RGB", (qr_width, total_height), "white")
    img_final.paste(img_qr, (0, 0))

    draw = ImageDraw.Draw(img_final)
    text_x = (qr_width - text_width) // 2
    text_y = qr_height + 20
    draw.text((text_x, text_y), text, fill="black", font=font)

    # Guardar
    if not os.path.exists(carpeta_qr):
        os.makedirs(carpeta_qr)

    ruta_qr = os.path.join(carpeta_qr, f"qr_caja_{id_caja}.png")
    img_final.save(ruta_qr)
    return ruta_qr

@bp.route('/cajas', methods=['GET', 'POST'])
def cajas():
    db = get_db()
    resultado = []
    termino = ''
    modo_crear = False
    cajas_buscadas = []
    termino_caja = ''

    # Crear nueva caja desde el formulario principal
    if request.method == 'POST' and 'nombre' in request.form and 'termino' not in request.form:
        nombre = request.form['nombre'].strip()
        if not nombre:
            flash('El nombre de la caja es obligatorio', 'error')
        else:
            existe = db.execute(
                'SELECT id FROM cajas WHERE LOWER(nombre) = ?',
                (nombre.lower(),)
            ).fetchone()
            if existe:
                flash('Ya existe una caja con ese nombre.', 'error')
            else:
                cursor = db.execute('INSERT INTO cajas (nombre) VALUES (?)', (nombre,))
                db.commit()

                id_caja = cursor.lastrowid

                carpeta_qr = os.path.join(current_app.root_path, 'databases', 'qr')
                generar_qr_con_id(id_caja, carpeta_qr)

                flash('Caja creada con éxito y QR generado.', 'success')

        return redirect(url_for('main.cajas'))

    # Crear nuevo objeto desde modo_crear
    if request.method == 'POST' and 'confirmar_creacion' in request.form:
        termino = request.form.get('termino', '').strip()
        cantidad = int(request.form.get('cantidad', 0))
        caja_id = request.form.get('caja_id')
        nueva_caja = request.form.get('nueva_caja', '').strip()

        if nueva_caja:
            cursor = db.execute('INSERT INTO cajas (nombre) VALUES (?)', (nueva_caja,))
            db.commit()
            caja_id = cursor.lastrowid

            carpeta_qr = os.path.join(current_app.root_path, 'databases', 'qr')
            generar_qr_con_id(caja_id, carpeta_qr)

        if not caja_id:
            flash('Debes seleccionar una caja existente o crear una nueva.', 'error')
        else:
            db.execute(
                'INSERT INTO objetos (nombre, cantidad, caja_id) VALUES (?, ?, ?)',
                (termino, cantidad, caja_id)
            )
            db.commit()
            flash(f'Objeto "{termino}" creado correctamente.', 'success')

        return redirect(url_for('main.cajas', termino=termino))

    # Buscar objeto por nombre exacto
    if request.method == 'GET' and 'termino' in request.args:
        termino = request.args.get('termino', '').strip().lower()
        if termino:
            resultado = db.execute("""
            SELECT objetos.id, objetos.nombre, objetos.cantidad, cajas.nombre AS caja_nombre, cajas.id AS caja_id
            FROM objetos
            JOIN cajas ON objetos.caja_id = cajas.id
            WHERE LOWER(objetos.nombre) LIKE ?
        """, (f'%{termino}%',)).fetchall()

            if not resultado:
                modo_crear = True
        else:
            flash('Introduce un término de búsqueda.', 'warning')

    # Buscar caja por ID o nombre parcial (sin importar mayúsculas/minúsculas)
    if request.method == 'GET' and 'busqueda_caja' in request.args:
        termino_caja = request.args.get('busqueda_caja', '').strip()
        if termino_caja:
            cajas_buscadas = db.execute(
                '''
                SELECT * FROM cajas
                WHERE CAST(id AS TEXT) LIKE ?
                OR LOWER(nombre) LIKE ?
                ''',
                (f'%{termino_caja}%', f'%{termino_caja.lower()}%')
            ).fetchall()

            if not cajas_buscadas:
                flash(f'No se encontraron cajas para "{termino_caja}"', 'warning')


    # Lista de todas las cajas
    cajas = db.execute('SELECT * FROM cajas ORDER BY nombre').fetchall()

    return render_template(
        'cajas.html',
        cajas=cajas,
        resultado=resultado,
        termino=termino,
        modo_crear=modo_crear,
        cajas_buscadas=cajas_buscadas,
        termino_caja=termino_caja
    )

@bp.route('/cajas/<int:caja_id>/editar', methods=['GET', 'POST'])
def editar_caja(caja_id):
    db = get_db()
    caja = db.execute('SELECT * FROM cajas WHERE id = ?', (caja_id,)).fetchone()
    if not caja:
        flash('Caja no encontrada', 'error')
        return redirect(url_for('main.cajas'))
    
    if request.method == 'POST':
        nuevo_nombre = request.form['nombre']
        if not nuevo_nombre:
            flash('El nombre no puede estar vacío', 'error')
        else:
            db.execute('UPDATE cajas SET nombre = ? WHERE id = ?', (nuevo_nombre, caja_id))
            db.commit()
            flash('Caja actualizada correctamente', 'success')
            return redirect(url_for('main.cajas'))
    return render_template('editar_caja.html', caja=caja)

@bp.route('/cajas/<int:caja_id>/eliminar', methods=['POST'])
def eliminar_caja(caja_id):
    db = get_db()

    # Eliminar la caja y sus objetos
    db.execute('DELETE FROM objetos WHERE caja_id = ?', (caja_id,))
    db.execute('DELETE FROM cajas WHERE id = ?', (caja_id,))
    db.commit()

    # Ruta base de QR
    carpeta_qr = os.path.join('app', 'databases', 'qr')
    nombre_qr = f"qr_caja_{caja_id}.png"
    ruta_qr = os.path.join(carpeta_qr, nombre_qr)

    # Mover a qr/borrados si existe
    if os.path.exists(ruta_qr):
        carpeta_borrados = os.path.join(carpeta_qr, 'borrados')
        os.makedirs(carpeta_borrados, exist_ok=True)
        shutil.move(ruta_qr, os.path.join(carpeta_borrados, nombre_qr))

    flash('Caja eliminada y QR archivado', 'success')
    
    
    return redirect(url_for('main.cajas'))

@bp.route('/api/objeto/<int:objeto_id>', methods=['POST'])
def actualizar_cantidad_objeto(objeto_id):
    # Paso 1: obtener la cantidad enviada por el fetch POST
    nueva_cantidad = request.form.get('cantidad')
    if nueva_cantidad is None:
        return 'Cantidad no proporcionada', 400

    # Paso 2: obtener db y hacer update
    db = get_db()
    db.execute('UPDATE objetos SET cantidad = ? WHERE id = ?', (nueva_cantidad, objeto_id))
    db.commit()

    # Paso 3: devolver respuesta vacía con código 204 (sin contenido)
    return '', 204

@bp.route('/cajas/<int:caja_id>', methods=['GET', 'POST'])
def ver_caja(caja_id):
    db = get_db()

    if request.method == 'POST':
        accion = request.form.get('accion')

        if accion == 'borrar':
            objeto_ids = request.form.getlist('objeto_ids')
            if objeto_ids:
                db.executemany('DELETE FROM objetos WHERE id = ?', [(obj_id,) for obj_id in objeto_ids])
                db.commit()
                flash(f'Se borraron {len(objeto_ids)} objetos.', 'success')
            return redirect(url_for('main.ver_caja', caja_id=caja_id))

        elif accion == 'mover':
            objeto_ids = request.form.getlist('objeto_ids')
            caja_destino = request.form.get('caja_destino')

            if not caja_destino:
                flash('Debe seleccionar una caja destino para mover los objetos.', 'error')
                return redirect(url_for('main.ver_caja', caja_id=caja_id))

            if objeto_ids:
                for obj_id in objeto_ids:
                    objeto = db.execute('SELECT * FROM objetos WHERE id = ?', (obj_id,)).fetchone()
                    if objeto:
                        # Buscar objeto igual (nombre) en la caja destino, sin diferenciar mayúsculas
                        obj_destino = db.execute(
                            'SELECT * FROM objetos WHERE caja_id = ? AND LOWER(nombre) = LOWER(?)',
                            (caja_destino, objeto['nombre'])
                        ).fetchone()

                        if obj_destino:
                            # Sumar cantidades y borrar objeto original
                            nueva_cantidad = objeto['cantidad'] + obj_destino['cantidad']
                            db.execute('UPDATE objetos SET cantidad = ? WHERE id = ?', (nueva_cantidad, obj_destino['id']))
                            db.execute('DELETE FROM objetos WHERE id = ?', (obj_id,))
                        else:
                            # Mover objeto a caja destino
                            db.execute('UPDATE objetos SET caja_id = ? WHERE id = ?', (caja_destino, obj_id))
                db.commit()
                flash(f'Se movieron {len(objeto_ids)} objetos a la caja seleccionada.', 'success')
            else:
                flash('No seleccionaste ningún objeto para mover.', 'warning')

            return redirect(url_for('main.ver_caja', caja_id=caja_id))

        else:
            # Actualizar cantidades
            updated = False
            for key, value in request.form.items():
                if key.startswith('objeto_'):
                    try:
                        obj_id = int(key.split('_')[1])
                        cantidad = int(value)
                        if cantidad < 0:
                            cantidad = 0
                        db.execute('UPDATE objetos SET cantidad = ? WHERE id = ?', (cantidad, obj_id))
                        updated = True
                    except ValueError:
                        continue
            if updated:
                db.commit()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'status': 'success'})
                else:
                    flash('Objetos actualizados correctamente.', 'success')
                    return redirect(url_for('main.ver_caja', caja_id=caja_id))

    objetos = db.execute('SELECT * FROM objetos WHERE caja_id = ?', (caja_id,)).fetchall()
    caja = db.execute('SELECT * FROM cajas WHERE id = ?', (caja_id,)).fetchone()
    cajas = db.execute('SELECT * FROM cajas ORDER BY nombre').fetchall()

    return render_template('ver_caja.html', objetos=objetos, caja=caja, cajas=cajas)

@bp.route('/cajas/<int:caja_id>/qr')
def ver_qr_caja(caja_id):
    import os
    from flask import current_app, send_from_directory, abort

    qr_folder = os.path.join(current_app.root_path, 'databases', 'qr')
    filename = f"qr_caja_{caja_id}.png"  # Cambia aquí el nombre esperado
    file_path = os.path.join(qr_folder, filename)
    if not os.path.isfile(file_path):
        abort(404)
    return send_from_directory(qr_folder, filename)

@bp.route('/cajas/<int:caja_id>/add_objeto', methods=['POST'])
def add_objeto(caja_id):
    nombre = request.form.get('nombre', '').strip()
    try:
        cantidad = int(request.form.get('cantidad', 0))
    except ValueError:
        cantidad = 0

    confirmar = request.form.get('confirmar', 'no')

    print("➡️ nombre:", nombre)
    print("➡️ cantidad:", cantidad)
    print("➡️ confirmar:", confirmar)

    if not nombre:
        flash('El nombre del objeto es obligatorio.', 'error')
        return redirect(url_for('main.ver_caja', caja_id=caja_id))

    db = get_db()

    coincidencias = db.execute('''
        SELECT objetos.id, objetos.cantidad, cajas.nombre AS caja_nombre, objetos.caja_id
        FROM objetos
        JOIN cajas ON cajas.id = objetos.caja_id
        WHERE LOWER(objetos.nombre) = LOWER(?)
    ''', (nombre.lower(),)).fetchall()

    en_misma_caja = next((o for o in coincidencias if o['caja_id'] == caja_id), None)

    print("➡️ coincidencias:", coincidencias)
    print("➡️ en_misma_caja:", en_misma_caja)

    if coincidencias and confirmar != 'si':
        print("🟡 Mostrando pantalla de confirmación")
        return render_template(
            'confirmar_objeto.html',
            nombre=nombre,
            cantidad=cantidad,
            coincidencias=coincidencias,
            caja_actual_id=caja_id
        )

    if en_misma_caja:
        nueva_cantidad = en_misma_caja['cantidad'] + cantidad
        db.execute(
            'UPDATE objetos SET cantidad = ? WHERE id = ?',
            (nueva_cantidad, en_misma_caja['id'])
        )
    else:
        db.execute(
            'INSERT INTO objetos (caja_id, nombre, cantidad) VALUES (?, ?, ?)',
            (caja_id, nombre, cantidad)
        )

    db.commit()
    flash('Objeto añadido correctamente.', 'success')
    return redirect(url_for('main.ver_caja', caja_id=caja_id))

@bp.route('/cajas/<int:caja_id>/accion_objetos', methods=['POST'])
def accion_objetos(caja_id):
    accion = request.form.get('accion')
    objeto_ids = request.form.getlist('objeto_ids')

    if not objeto_ids:
        flash('No seleccionaste ningún objeto.', 'warning')
        return redirect(url_for('main.ver_caja', caja_id=caja_id))

    db = get_db()

    if accion == 'borrar':
        # Borrar objetos seleccionados
        query = 'DELETE FROM objetos WHERE id IN ({seq})'.format(
            seq=','.join(['?']*len(objeto_ids))
        )
        db.execute(query, objeto_ids)
        db.commit()
        flash(f'Se borraron {len(objeto_ids)} objetos.', 'success')
        return redirect(url_for('main.ver_caja', caja_id=caja_id))

    # Si no borrar, redirigir (mover se hace en otro endpoint)
    flash('Acción no reconocida.', 'error')
    return redirect(url_for('main.ver_caja', caja_id=caja_id))

@bp.route('/cajas/<int:caja_id>/mover_objetos', methods=['POST'])
def mover_objetos(caja_id):
    caja_destino_id = request.form.get('caja_destino_id')
    objeto_ids = request.form.getlist('objeto_ids')

    if not objeto_ids or not caja_destino_id:
        flash('Faltan datos para mover los objetos.', 'error')
        return redirect(url_for('main.ver_caja', caja_id=caja_id))

    db = get_db()

    for obj_id in objeto_ids:
        try:
            cantidad_a_mover = int(request.form.get(f'cantidad_{obj_id}', 0))
            if cantidad_a_mover <= 0:
                continue
        except ValueError:
            continue

        # Obtener objeto actual para validar
        obj = db.execute('SELECT caja_id, cantidad, nombre FROM objetos WHERE id = ?', (obj_id,)).fetchone()
        if not obj or obj['caja_id'] != caja_id:
            continue  # no existe o no es de esta caja

        if cantidad_a_mover > obj['cantidad']:
            flash(f'No puedes mover más unidades de {obj["nombre"]} de las que hay.', 'error')
            return redirect(url_for('main.ver_caja', caja_id=caja_id))

        # Restar cantidad en caja origen
        nueva_cantidad_origen = obj['cantidad'] - cantidad_a_mover
        if nueva_cantidad_origen == 0:
            db.execute('DELETE FROM objetos WHERE id = ?', (obj_id,))
        else:
            db.execute('UPDATE objetos SET cantidad = ? WHERE id = ?', (nueva_cantidad_origen, obj_id))

        # Añadir o actualizar objeto en caja destino
        obj_destino = db.execute(
            'SELECT id, cantidad FROM objetos WHERE caja_id = ? AND LOWER(nombre) = ?',
            (caja_destino_id, obj['nombre'].lower())
        ).fetchone()

        if obj_destino:
            nueva_cantidad_destino = obj_destino['cantidad'] + cantidad_a_mover
            db.execute('UPDATE objetos SET cantidad = ? WHERE id = ?', (nueva_cantidad_destino, obj_destino['id']))
        else:
            db.execute(
                'INSERT INTO objetos (caja_id, nombre, cantidad) VALUES (?, ?, ?)',
                (caja_destino_id, obj['nombre'], cantidad_a_mover)
            )

    db.commit()
    flash(f'Objetos movidos exitosamente.', 'success')
    return redirect(url_for('main.ver_caja', caja_id=caja_id))

@bp.route('/qr_reader')
def qr_reader():
    return render_template('qr_reader.html')

@bp.route('/api/objeto/<int:objeto_id>')
def api_objeto(objeto_id):
    db = get_db()
    obj = db.execute('SELECT * FROM objetos WHERE id = ?', (objeto_id,)).fetchone()
    return jsonify(dict(obj)) if obj else ('', 404)

@bp.route('/buscar_objeto', methods=['GET', 'POST'])
@bp.route('/cajas/<int:caja_id>/buscar_objeto', methods=['GET', 'POST'])
def buscar_objeto(caja_id=None):
    db = get_db()
    resultado = []
    cajas = db.execute('SELECT id, nombre FROM cajas').fetchall()
    termino = ''
    modo_crear = False

    def quitar_tildes(texto):
        import unicodedata
        return ''.join(
            c for c in unicodedata.normalize('NFD', texto)
            if unicodedata.category(c) != 'Mn'
        )

    if request.method == 'POST':
        termino = request.form.get('termino', '').strip().lower()
        termino_sin_tilde = quitar_tildes(termino)

        if not termino:
            flash('Por favor ingresa un término de búsqueda.', 'error')
            return redirect(request.url)

        if 'confirmar_creacion' in request.form:
            caja_seleccionada = request.form.get('caja_id') or caja_id
            nueva_caja_nombre = request.form.get('nueva_caja')
            cantidad = int(request.form.get('cantidad', 0))

            if nueva_caja_nombre:
                nueva_caja_nombre = nueva_caja_nombre.strip()
                caja_existente = db.execute(
                    'SELECT id FROM cajas WHERE LOWER(nombre) = ?',
                    (nueva_caja_nombre.lower(),)
                ).fetchone()
                if caja_existente:
                    caja_seleccionada = caja_existente['id']
                else:
                    db.execute('INSERT INTO cajas (nombre) VALUES (?)', (nueva_caja_nombre,))
                    db.commit()
                    caja_seleccionada = db.execute('SELECT last_insert_rowid()').fetchone()[0]

            if caja_seleccionada:
                db.execute(
                    'INSERT INTO objetos (caja_id, nombre, cantidad) VALUES (?, ?, ?)',
                    (int(caja_seleccionada), termino, cantidad)
                )
                db.commit()
                flash(f'Objeto "{termino}" creado con éxito.', 'success')
                return redirect(request.url)

        else:
            # Buscar objetos (filtrado por caja si existe)
            query = """
                SELECT objetos.id, objetos.nombre, objetos.cantidad, cajas.nombre AS caja_nombre, cajas.id AS caja_id
                FROM objetos
                JOIN cajas ON objetos.caja_id = cajas.id
            """
            params = ()
            if caja_id:
                query += " WHERE objetos.caja_id = ?"
                params = (caja_id,)

            todos_objetos = db.execute(query, params).fetchall()

            resultado = [
                r for r in todos_objetos
                if termino_sin_tilde in quitar_tildes(r['nombre'].lower())
            ]

            if not resultado:
                modo_crear = True
                flash('No se encontraron resultados. Puedes crear el objeto.', 'info')

    else:
        termino = request.args.get('termino', '').strip().lower()
        termino_sin_tilde = quitar_tildes(termino)

        query = """
            SELECT objetos.id, objetos.nombre, objetos.cantidad, cajas.nombre AS caja_nombre, cajas.id AS caja_id
            FROM objetos
            JOIN cajas ON objetos.caja_id = cajas.id
        """
        params = ()
        if caja_id:
            query += " WHERE objetos.caja_id = ?"
            params = (caja_id,)

        if termino:
            todos_objetos = db.execute(query, params).fetchall()

            resultado = [
                r for r in todos_objetos
                if termino_sin_tilde in quitar_tildes(r['nombre'].lower())
            ]

            if not resultado:
                modo_crear = True
                flash('No se encontraron resultados. Puedes crear el objeto.', 'info')

    return render_template(
        'buscar_objeto.html',
        resultado=resultado,
        cajas=cajas,
        termino=termino,
        modo_crear=modo_crear,
        caja_actual_id=caja_id
    )

@bp.route('/buscar_caja', methods=['GET'])
def buscar_caja():
    db = get_db()

    codigo = request.args.get('codigo')
    busqueda_caja = request.args.get('busqueda_caja')

    if codigo:
        # Buscar caja por ID exacto
        try:
            caja_id = int(codigo)
        except (ValueError, TypeError):
            return {'error': 'Código inválido'}, 400

        caja = db.execute('SELECT * FROM cajas WHERE id = ?', (caja_id,)).fetchone()
        if caja:
            return {'redirect_url': url_for('main.ver_caja', caja_id=caja_id)}
        else:
            return {'error': 'Caja no encontrada'}, 404

    elif busqueda_caja:
        termino = busqueda_caja.strip()
        if termino:
            cajas_buscadas = db.execute(
                '''
                SELECT * FROM cajas
                WHERE CAST(id AS TEXT) LIKE ?
                OR LOWER(nombre) LIKE ?
                ''',
                (f'%{termino}%', f'%{termino.lower()}%')
            ).fetchall()

            if cajas_buscadas:
                # Devuelve resultados o maneja como quieras, por ejemplo:
                return {'cajas': [dict(id=c['id'], nombre=c['nombre']) for c in cajas_buscadas]}
            else:
                return {'error': 'No se encontraron cajas'}, 404

    else:
        return {'error': 'Parámetro requerido'}, 400





def borrar_objetos(caja_id):

    
    objeto_ids = request.form.getlist('objeto_ids')
    if not objeto_ids:
        flash('No seleccionaste objetos para borrar.', 'warning')
        return redirect(url_for('main.ver_caja', caja_id=caja_id))

    db = get_db()
    query = f'DELETE FROM objetos WHERE id IN ({",".join(["?"]*len(objeto_ids))})'
    db.execute(query, objeto_ids)
    db.commit()
    flash(f'Se borraron {len(objeto_ids)} objetos.', 'success')
    return ('', 204)  # respuesta vacía con status 204 para fetch