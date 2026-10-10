# Cards TCG — MySQL con usuario administrador

## Qué incluye
Tienda negra/dorada, catálogo público, carrito y pedidos por WhatsApp. El panel **Administrar** requiere **usuario y contraseña**. Solo una sesión autenticada puede agregar, editar o eliminar cartas, cambiar WhatsApp o gestionar pedidos. Los productos se guardan en MySQL.

## Importación SQL (cPanel)
1. En phpMyAdmin selecciona `grupoip1_cardstcg`.
2. Importa `cards_tcg_mysql.sql`. No elimina tablas ni pedidos existentes.
3. Verifica `products`, `orders`, `settings`, `sessions`, `admin_users`.

## Configuración
1. Instala Python 3.11+ y `pip install -r requirements.txt`.
2. Define variables de `.env.example` en el entorno del proceso (el archivo .env no se carga automáticamente).
3. **Rota la contraseña MySQL compartida previamente en el chat** y configura la nueva exclusivamente como variable de entorno.
4. Configura `ADMIN_USERNAME` y `ADMIN_PASSWORD` (mínimo 12 caracteres) ANTES del primer arranque.
5. Ejecuta `python server.py`. Visita `http://localhost:8000`, pulsa **Administrar** e inicia sesión.

El primer inicio crea la cuenta administradora si la tabla `admin_users` está vacía. Cambiar ADMIN_PASSWORD después no modifica la contraseña ya guardada. No borres cuentas para restablecer contraseñas sin respaldo.

## Importante para producción
Este servidor HTTP incorporado sirve para desarrollo y pruebas; **no debe exponerse directamente a Internet**. Para cPanel hay que adaptar la aplicación a WSGI/Passenger o usar un servidor/proxy compatible. Configura HTTPS real, cookies seguras (`HTTPS=1`), TLS validado hacia MySQL, respaldos y limitación de intentos persistente antes de publicar. `MYSQL_SSL=true` solicita TLS, pero verifica que el certificado y nombre del servidor sean válidos; no supongas que una IP por sí sola garantiza validación. El flujo de pedidos descuenta stock al registrar un pedido pendiente; revisa cancelaciones manualmente.

## Nota
No se insertan cartas ficticias automáticamente. Solo el administrador agrega cartas reales desde el panel.

## Crear administrador mediante código (recomendado)
Después de importar `cards_tcg_mysql.sql`, define `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD` y `MYSQL_SSL` como variables de entorno. Ejecuta:

```bash
python crear_administrador.py --usuario admin
```

El programa solicita dos veces una contraseña de 12+ caracteres sin mostrarla, crea o actualiza `admin_users` usando hash scrypt con sal aleatoria e invalida las sesiones previas. **No escribas la contraseña en código ni SQL**. Luego ejecuta `python server.py`; si ya existe un administrador, el servidor no necesita `ADMIN_PASSWORD`. No ejecutes `crear_administrador.py` desde una ruta web pública.
