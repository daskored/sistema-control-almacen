# Sistema de Control de Movimientos de Almacén

Proyecto académico individual en Python y Flask. Controla productos, entradas, salidas, existencias e historial con roles de supervisor y almacenista.

## Funciones
- Inicio de sesión con contraseñas protegidas mediante hash.
- Supervisor: registra productos (stock inicial 0), usuarios y consulta el historial global.
- Supervisor y almacenista: consultan inventario y registran entradas/salidas.
- Las salidas requieren un motivo: venta, uso interno, devolución u otro.
- No se permiten cantidades no positivas ni salidas superiores al stock.
- Cada operación exitosa crea un movimiento nuevo; no hay opción de editar ni eliminar movimientos.

## Desarrollo local (opcional)
```bash
python -m venv .venv
pip install -r requirements.txt
# Configurar SECRET_KEY, ADMIN_USER y ADMIN_PASSWORD
python app.py
pytest --cov=app --cov-report=term-missing
```

## Despliegue en Render
1. Subir todos los archivos del proyecto a un repositorio GitHub (incluidas carpetas).
2. Crear una base PostgreSQL en Render o un proveedor PostgreSQL compatible; copiar su URL de conexión.
3. En Render, crear **Web Service** conectado al repositorio, entorno Python.
4. **Build Command:** `pip install -r requirements.txt`
5. **Start Command:** `gunicorn app:app`
6. Variables de entorno obligatorias: `DATABASE_URL` (URL de PostgreSQL), `SECRET_KEY` (cadena larga aleatoria), `ADMIN_USER` (usuario inicial), `ADMIN_PASSWORD` (contraseña inicial robusta).
7. Desplegar. El supervisor inicial se crea únicamente si la tabla de usuarios está vacía. La ruta `/health` responde con JSON para comprobar disponibilidad.

**Atención:** no usar SQLite para producción en Render: el almacenamiento del servicio puede ser efímero. No subir contraseñas ni secretos al repositorio. Si el servicio ya tiene usuarios, cambiar `ADMIN_PASSWORD` en variables de entorno no modifica las contraseñas guardadas.

## Pruebas
```bash
pytest -q --cov=app --cov-report=term-missing
```
Las pruebas cubren reglas de stock, movimientos, login y permisos. La cobertura real debe medirse ejecutándolas; no se declara un porcentaje sin resultados.

## Estructura
- `app.py`: modelos, lógica de negocio, rutas web.
- `templates/` y `static/`: interfaz web.
- `tests/`: pruebas automatizadas.
- `docs/`: notas de proceso y bitácora de IA.

## Limitaciones actuales
Primera versión académica. Antes de utilizar en un almacén real se requiere endurecer seguridad (CSRF, control de sesiones, rate limiting), manejo robusto de concurrencia y operaciones administrativas de corrección/auditoría. No se recomienda usar con datos reales sensibles.
