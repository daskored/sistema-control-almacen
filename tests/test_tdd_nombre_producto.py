
from app import validar_nombre_producto


def test_rechazar_nombre_producto_vacio():
    assert validar_nombre_producto("") is False


def test_rechazar_nombre_con_espacios():
    assert validar_nombre_producto("   ") is False


def test_aceptar_nombre_valido():
    assert validar_nombre_producto("Filtro de aceite") is True
