import pytest
from werkzeug.security import generate_password_hash
from app import create_app, DB, Usuario, Producto

@pytest.fixture
def app():
    application = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://', 'SECRET_KEY': 'test-secret'})
    with application.app_context():
        DB.drop_all()
        DB.create_all()
        DB.session.add_all([
            Usuario(id=1, nombre='Laura', usuario='laura', password_hash=generate_password_hash('clave12345'), rol='supervisor'),
            Usuario(id=2, nombre='Carlos', usuario='carlos', password_hash=generate_password_hash('clave12345'), rol='almacenista'),
            Producto(id=1, codigo='P01', nombre='Tornillos', existencias=15),
        ])
        DB.session.commit()
    yield application
    with application.app_context():
        DB.session.remove()
        DB.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()
