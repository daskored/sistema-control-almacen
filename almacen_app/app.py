import os
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint
from werkzeug.security import check_password_hash, generate_password_hash

DB = SQLAlchemy()

class Usuario(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    nombre = DB.Column(DB.String(100), nullable=False)
    usuario = DB.Column(DB.String(50), unique=True, nullable=False)
    password_hash = DB.Column(DB.String(255), nullable=False)
    rol = DB.Column(DB.String(20), nullable=False)

class Producto(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    codigo = DB.Column(DB.String(40), unique=True, nullable=False)
    nombre = DB.Column(DB.String(120), nullable=False)
    existencias = DB.Column(DB.Integer, nullable=False, default=0)
    __table_args__ = (CheckConstraint('existencias >= 0', name='stock_no_negativo'),)

    def puede_descontar(self, cantidad):
        return isinstance(cantidad, int) and cantidad > 0 and self.existencias >= cantidad

class Movimiento(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    tipo = DB.Column(DB.String(10), nullable=False)
    cantidad = DB.Column(DB.Integer, nullable=False)
    motivo = DB.Column(DB.String(30))
    fecha_hora = DB.Column(DB.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    usuario_id = DB.Column(DB.Integer, DB.ForeignKey('usuario.id'), nullable=False)
    producto_id = DB.Column(DB.Integer, DB.ForeignKey('producto.id'), nullable=False)
    usuario_rel = DB.relationship('Usuario')
    producto_rel = DB.relationship('Producto')
    __table_args__ = (CheckConstraint('cantidad > 0', name='cantidad_positiva'),)

MOTIVOS = ('venta', 'uso interno', 'devolución', 'otro')

class ErrorMovimiento(ValueError):
    pass

class ServicioMovimientos:
    @staticmethod
    def registrar(producto, usuario, tipo, cantidad, motivo=None):
        if tipo not in ('entrada', 'salida'):
            raise ErrorMovimiento('Tipo de movimiento inválido.')
        if not isinstance(cantidad, int) or cantidad <= 0:
            raise ErrorMovimiento('La cantidad debe ser un entero positivo.')
        if tipo == 'salida' and motivo not in MOTIVOS:
            raise ErrorMovimiento('Selecciona un motivo de salida válido.')
        if tipo == 'salida' and not producto.puede_descontar(cantidad):
            raise ErrorMovimiento(f'Existencias insuficientes. Disponibles: {producto.existencias}.')
        if tipo == 'entrada':
            producto.existencias += cantidad
        else:
            producto.existencias -= cantidad
        mov = Movimiento(tipo=tipo, cantidad=cantidad, motivo=motivo if tipo == 'salida' else None,
                         usuario_id=usuario.id, producto_id=producto.id)
        DB.session.add(mov)
        try:
            DB.session.commit()
        except Exception:
            DB.session.rollback()
            raise
        return mov


def create_app(test_config=None):
    app = Flask(__name__)
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///almacen.db')
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY', 'solo-desarrollo-cambiar'),
                      SQLALCHEMY_DATABASE_URI=db_url, SQLALCHEMY_TRACK_MODIFICATIONS=False)
    if test_config:
        app.config.update(test_config)
    DB.init_app(app)
    with app.app_context():
        DB.create_all()
        if not Usuario.query.first() and not app.config.get('TESTING'):
            user = os.environ.get('ADMIN_USER')
            pwd = os.environ.get('ADMIN_PASSWORD')
            if user and pwd:
                DB.session.add(Usuario(nombre='Supervisor', usuario=user, password_hash=generate_password_hash(pwd), rol='supervisor'))
                DB.session.commit()

    def require_login(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if 'uid' not in session:
                return redirect(url_for('login'))
            return view(*args, **kwargs)
        return wrapper

    def require_supervisor(view):
        @wraps(view)
        @require_login
        def wrapper(*args, **kwargs):
            user = DB.session.get(Usuario, session['uid'])
            if not user or user.rol != 'supervisor':
                flash('Acceso exclusivo para supervisores.', 'error')
                return redirect(url_for('inicio'))
            return view(*args, **kwargs)
        return wrapper

    @app.route('/health')
    def health():
        return {'status': 'ok'}

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            user = Usuario.query.filter_by(usuario=request.form.get('usuario', '').strip()).first()
            if user and check_password_hash(user.password_hash, request.form.get('password', '')):
                session.clear()
                session['uid'] = user.id
                session['nombre'] = user.nombre
                session['rol'] = user.rol
                return redirect(url_for('inicio'))
            flash('Credenciales incorrectas.', 'error')
        return render_template('login.html')

    @app.route('/logout', methods=['POST'])
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.route('/')
    @require_login
    def inicio():
        return render_template('inicio.html', productos=Producto.query.order_by(Producto.nombre).all())

    @app.route('/productos/nuevo', methods=['GET', 'POST'])
    @require_supervisor
    def nuevo_producto():
        if request.method == 'POST':
            codigo = request.form.get('codigo', '').strip()
            nombre = request.form.get('nombre', '').strip()
            if not codigo or not nombre:
                flash('Código y nombre son obligatorios.', 'error')
            elif Producto.query.filter_by(codigo=codigo).first():
                flash('Ya existe un producto con ese código.', 'error')
            else:
                DB.session.add(Producto(codigo=codigo, nombre=nombre, existencias=0))
                DB.session.commit()
                flash('Producto creado con 0 existencias.', 'success')
                return redirect(url_for('inicio'))
        return render_template('producto.html')

    @app.route('/movimientos/nuevo', methods=['GET', 'POST'])
    @require_login
    def nuevo_movimiento():
        productos = Producto.query.order_by(Producto.nombre).all()
        if request.method == 'POST':
            try:
                producto = DB.session.get(Producto, int(request.form.get('producto_id', '')))
                if not producto:
                    raise ErrorMovimiento('Producto inexistente.')
                cantidad = int(request.form.get('cantidad', ''))
                usuario = DB.session.get(Usuario, session['uid'])
                ServicioMovimientos.registrar(producto, usuario, request.form.get('tipo'), cantidad,
                                              request.form.get('motivo'))
                flash('Movimiento registrado correctamente.', 'success')
                return redirect(url_for('inicio'))
            except (ValueError, TypeError) as exc:
                DB.session.rollback()
                flash(str(exc) if isinstance(exc, ErrorMovimiento) else 'Introduce una cantidad entera válida.', 'error')
        return render_template('movimiento.html', productos=productos, motivos=MOTIVOS)

    @app.route('/historial')
    @require_supervisor
    def historial():
        movimientos = Movimiento.query.order_by(Movimiento.fecha_hora.desc(), Movimiento.id.desc()).all()
        return render_template('historial.html', movimientos=movimientos)

    @app.route('/usuarios/nuevo', methods=['GET', 'POST'])
    @require_supervisor
    def nuevo_usuario():
        if request.method == 'POST':
            nombre = request.form.get('nombre', '').strip()
            username = request.form.get('usuario', '').strip()
            password = request.form.get('password', '')
            rol = request.form.get('rol')
            if not nombre or not username or len(password) < 8 or rol not in ('supervisor', 'almacenista'):
                flash('Completa los datos; contraseña de al menos 8 caracteres.', 'error')
            elif Usuario.query.filter_by(usuario=username).first():
                flash('Ese usuario ya existe.', 'error')
            else:
                DB.session.add(Usuario(nombre=nombre, usuario=username, password_hash=generate_password_hash(password), rol=rol))
                DB.session.commit()
                flash('Usuario creado.', 'success')
                return redirect(url_for('inicio'))
        return render_template('usuario.html')

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
