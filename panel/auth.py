"""Autenticación del panel: hash de contraseñas con bcrypt y sesión por cookie firmada."""

import bcrypt
from fastapi import Request

# bcrypt solo usa los primeros 72 bytes de la contraseña; más largas se rechazan.
MAX_BYTES_PASSWORD = 72


def hashear_password(password: str) -> str:
    """Devuelve el hash bcrypt (texto) para guardar en usuarios.password_hash."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password: str, password_hash: str) -> bool:
    """True si la contraseña coincide con el hash. Si el hash no es un bcrypt válido
    (por ejemplo el 'hash_temporal_cambiar' de prueba), devuelve False."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


class NoAutenticado(Exception):
    """Se lanza cuando se pide una página protegida sin haber iniciado sesión."""


def usuario_actual(request: Request):
    """Devuelve el usuario guardado en la sesión (dict) o None."""
    return request.session.get("usuario")


def requerir_usuario(request: Request) -> dict:
    """Dependencia de FastAPI: protege una ruta. Si no hay sesión, main.py
    redirige a /login."""
    usuario = usuario_actual(request)
    if usuario is None:
        raise NoAutenticado()
    return usuario
