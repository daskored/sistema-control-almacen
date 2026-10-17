import pytest
from app import DB, Producto, Usuario, Movimiento, ServicioMovimientos, ErrorMovimiento

def test_stock_insuficiente_no_modifica_inventario(app):
    with app.app_context():
        p = DB.session.get(Producto, 1)
        with pytest.raises(ErrorMovimiento, match='insuficientes'):
            ServicioMovimientos.registrar(p, DB.session.get(Usuario, 2), 'salida', 20, 'venta')
        assert p.existencias == 15
        assert Movimiento.query.count() == 0

@pytest.mark.parametrize('cantidad', [0, -3])
def test_cantidad_no_positiva_rechazada(app, cantidad):
    with app.app_context():
        with pytest.raises(ErrorMovimiento, match='positivo'):
            ServicioMovimientos.registrar(DB.session.get(Producto, 1), DB.session.get(Usuario, 2), 'entrada', cantidad)

def test_salida_valida_y_historial_independiente(app):
    with app.app_context():
        p = DB.session.get(Producto, 1)
        u = DB.session.get(Usuario, 2)
        ServicioMovimientos.registrar(p, u, 'salida', 10, 'venta')
        ServicioMovimientos.registrar(p, u, 'salida', 5, 'uso interno')
        assert p.existencias == 0
        assert Movimiento.query.count() == 2
        assert [m.cantidad for m in Movimiento.query.order_by(Movimiento.id)] == [10, 5]

def test_entrada_aumenta_stock(app):
    with app.app_context():
        p = DB.session.get(Producto, 1)
        ServicioMovimientos.registrar(p, DB.session.get(Usuario, 2), 'entrada', 7)
        assert p.existencias == 22

def test_motivo_invalido_rechazado(app):
    with app.app_context():
        with pytest.raises(ErrorMovimiento, match='motivo'):
            ServicioMovimientos.registrar(DB.session.get(Producto, 1), DB.session.get(Usuario, 2), 'salida', 2, 'ninguno')

def login(client, usuario='carlos'):
    return client.post('/login', data={'usuario': usuario, 'password': 'clave12345'}, follow_redirects=True)

def test_login_y_salir(client):
    assert b'Iniciar sesi' in client.get('/login').data
    assert b'Inventario actual' in login(client).data
    client.post('/logout')
    assert client.get('/').status_code == 302

def test_almacenista_no_accede_a_historial(client):
    login(client)
    assert b'Acceso exclusivo' in client.get('/historial', follow_redirects=True).data

def test_supervisor_crea_producto_en_cero(client, app):
    login(client, 'laura')
    r = client.post('/productos/nuevo', data={'codigo':'P02','nombre':'Tuercas'}, follow_redirects=True)
    assert b'Tuercas' in r.data
    with app.app_context():
        assert Producto.query.filter_by(codigo='P02').first().existencias == 0

def test_registrar_salida_web(client, app):
    login(client)
    r = client.post('/movimientos/nuevo', data={'producto_id':1,'tipo':'salida','cantidad':3,'motivo':'venta'}, follow_redirects=True)
    assert b'Movimiento registrado' in r.data
    with app.app_context():
        assert DB.session.get(Producto, 1).existencias == 12

def test_salida_rechazada_web(client, app):
    login(client)
    r = client.post('/movimientos/nuevo', data={'producto_id':1,'tipo':'salida','cantidad':99,'motivo':'venta'}, follow_redirects=True)
    assert b'Existencias insuficientes' in r.data
    with app.app_context():
        assert DB.session.get(Producto, 1).existencias == 15
