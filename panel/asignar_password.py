"""Asigna una contraseña real (hasheada con bcrypt) a un usuario del panel.

La contraseña se pide por teclado sin mostrarla, así no queda en el historial
de la terminal ni en ningún archivo del proyecto.

Uso (desde C:\\tesis, en PowerShell):
    docker run -it --rm -v C:\\tesis:/app -w /app/panel -e DB_HOST=host.docker.internal tesis-panel python asignar_password.py
"""

import getpass

from auth import MAX_BYTES_PASSWORD, hashear_password
from db import conectar

LARGO_MINIMO = 8


def main():
    email = input("Correo del usuario [admin@turismo.test]: ").strip().lower()
    if not email:
        email = "admin@turismo.test"

    password = getpass.getpass("Nueva contraseña (no se muestra): ")
    repetida = getpass.getpass("Repite la contraseña: ")

    if password != repetida:
        print("Las contraseñas no coinciden. No se cambió nada.")
        return
    if len(password) < LARGO_MINIMO:
        print(f"La contraseña debe tener al menos {LARGO_MINIMO} caracteres. No se cambió nada.")
        return
    if len(password.encode("utf-8")) > MAX_BYTES_PASSWORD:
        print(f"La contraseña no puede superar {MAX_BYTES_PASSWORD} bytes. No se cambió nada.")
        return

    conn = conectar()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE usuarios SET password_hash = %s WHERE lower(email) = %s",
                (hashear_password(password), email),
            )
            actualizados = cur.rowcount
        conn.commit()
    finally:
        conn.close()

    if actualizados == 0:
        print(f"No existe ningún usuario con el correo {email}. No se cambió nada.")
    else:
        print(f"Contraseña actualizada para {email}.")


if __name__ == "__main__":
    main()
