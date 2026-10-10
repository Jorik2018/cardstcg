"""Crea o actualiza explícitamente el administrador de Cards TCG en MySQL.
Uso: python crear_administrador.py --usuario admin
Solicita contraseña sin mostrarla ni escribirla en archivos.
"""
import argparse
import getpass
import hashlib
import re
import secrets
import time
from server import conn

def main():
    parser = argparse.ArgumentParser(description='Crear o actualizar usuario administrador')
    parser.add_argument('--usuario', default='admin')
    args = parser.parse_args()
    username = args.usuario.strip()
    
    if not re.fullmatch(r'[A-Za-z0-9_.-]{3,80}', username):
        parser.error('El usuario debe tener entre 3 y 80 caracteres: letras, números, _, . o -')
        
    password = getpass.getpass('Nueva contraseña (mínimo 12 caracteres): ')
    confirm = getpass.getpass('Repite la contraseña: ')
    
    if len(password) < 12 or password != confirm:
        parser.error('Las contraseñas no coinciden o tienen menos de 12 caracteres')
        
    salt = secrets.token_bytes(16)
    hashed = salt.hex() + ':' + hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1).hex()
    
    with conn() as c:
        # Usamos c.execute directamente, ya que tu DBConnection lo envuelve
        c.execute(
            'INSERT INTO admin_users(username, password_hash, active, created) VALUES(%s, %s, 1, %s) '
            'ON DUPLICATE KEY UPDATE password_hash=VALUES(password_hash), active=1',
            (username, hashed, int(time.time()))
        )
        # Invalidar sesiones antiguas tras crear o cambiar credenciales.
        c.execute('DELETE FROM sessions')
        
    print('Administrador creado o actualizado correctamente:', username)

if __name__ == '__main__':
    main()