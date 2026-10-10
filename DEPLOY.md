# Cards TCG — preparación para Render + MySQL externo

**Estado:** preparado para pruebas de despliegue, no auditado para producción.

1. Subir el contenido de la carpeta `CardsTCG` a la raíz de un repositorio privado de GitHub.
2. Crear una base de datos MySQL 8 externa que acepte conexiones TLS desde Render y disponga de copias de seguridad.
3. En Render crear un Web Service desde el repositorio. Runtime Python; Root Directory vacío si los archivos están en la raíz; Build Command `pip install -r requirements.txt`; Start Command `python server.py`; plan Free.
4. Definir variables: `MYSQL_HOST`, `MYSQL_PORT=3306`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_SSL=true`, `ADMIN_PASSWORD` (12+ caracteres), `WHATSAPP_NUMBER` (prefijo país), `HTTPS=1`.
5. Confirmar conexión, creación de tablas, autenticación, CSRF, pedidos, persistencia, HTTPS y copias de seguridad antes de aceptar ventas.
6. No subir secretos a GitHub. No usar una base MySQL alojada en el propio sistema de archivos efímero de Render.

**Pendiente:** auditoría de seguridad y pruebas de integración contra MySQL real; configuración de proveedor externo de MySQL. El plan gratuito de Render entra en reposo por inactividad y no ofrece disponibilidad 24/7 garantizada.
