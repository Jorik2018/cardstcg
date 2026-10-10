import os,json,secrets,hashlib,hmac,time,re,threading,ssl
import pymysql
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
from http.cookies import SimpleCookie
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def cargar_configuracion_privada():
    archivo=ROOT/'.env'
    if not archivo.is_file():return
    for linea in archivo.read_text(encoding='utf-8').splitlines():
        linea=linea.strip()
        if not linea or linea.startswith('#') or '=' not in linea:continue
        clave,valor=linea.split('=',1)
        clave=clave.strip()
        if re.fullmatch(r'[A-Z][A-Z0-9_]*',clave):
            os.environ.setdefault(clave,valor.strip().strip('"').strip("'"))
cargar_configuracion_privada()

PORT=int(os.environ.get('PORT','8000'))
HTTPS=os.environ.get('HTTPS','0')=='1'
lock=threading.Lock(); attempts={}

class DBConnection:
    def __init__(self):
        url=os.environ.get('DATABASE_URL','')
        if url:
            from urllib.parse import urlsplit,unquote
            u=urlsplit(url)
            if u.scheme not in ('mysql','mysql+pymysql'):raise RuntimeError('DATABASE_URL debe comenzar con mysql://')
            params=dict(host=u.hostname,port=u.port or 3306,user=unquote(u.username or ''),password=unquote(u.password or ''),database=unquote(u.path.lstrip('/')))
        else:
            # Aquí se pueden usar tus credenciales fijas o las del archivo .env
            params=dict(
                host=os.environ.get('MYSQL_HOST','72.9.154.22'),
                port=int(os.environ.get('MYSQL_PORT','3306')),
                user=os.environ.get('MYSQL_USER','grupoip1_cardstcg'),
                password=os.environ.get('MYSQL_PASSWORD','v[s=MGl1}oBH2kbb'),
                database=os.environ.get('MYSQL_DATABASE','grupoip1_cardstcg')
            )
        
        # Configuración SSL segura para ignorar certificados autofirmados del servidor remoto
        if os.environ.get('MYSQL_SSL','true').lower() not in ('0','false','no'):
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            params['ssl'] = ssl_context

        self.db=pymysql.connect(**params,charset='utf8mb4',cursorclass=pymysql.cursors.DictCursor,autocommit=False,connect_timeout=10)
        self.lastrowid=None

    def __enter__(self):return self
    def __exit__(self,t,v,tb):
        try:self.db.rollback() if t else self.db.commit()
        finally:self.db.close()

    def execute(self,sql,args=()):
        sql=sql.replace('?', '%s').replace('BEGIN IMMEDIATE','START TRANSACTION')
        sql=sql.replace('INSERT INTO settings VALUES (%s,%s) ON CONFLICT(key) DO UPDATE SET value=excluded.value','INSERT INTO settings VALUES (%s,%s) ON DUPLICATE KEY UPDATE value=VALUES(value)')
        self.cur=self.db.cursor();self.cur.execute(sql,args);self.lastrowid=self.cur.lastrowid;return self

    def executemany(self,sql,rows):
        self.cur=self.db.cursor();self.cur.executemany(sql.replace('?', '%s'),rows);return self

    def fetchone(self):return self.cur.fetchone()
    def fetchall(self):return self.cur.fetchall()

    @property
    def rowcount(self):return self.cur.rowcount

    def __iter__(self):return iter(self.cur.fetchall())

def conn():return DBConnection()

def init():
    with conn() as c:
        c.execute('CREATE TABLE IF NOT EXISTS settings (`key` VARCHAR(100) PRIMARY KEY,`value` TEXT NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4')
        c.execute('CREATE TABLE IF NOT EXISTS products (id BIGINT PRIMARY KEY AUTO_INCREMENT,name VARCHAR(120) NOT NULL,collection VARCHAR(100) NOT NULL DEFAULT "",rarity VARCHAR(80) NOT NULL DEFAULT "",price DECIMAL(12,2) NOT NULL,stock INT NOT NULL,image TEXT NOT NULL,description TEXT NOT NULL,featured TINYINT NOT NULL DEFAULT 0,created BIGINT NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4')
        c.execute('CREATE TABLE IF NOT EXISTS admin_users (id BIGINT PRIMARY KEY AUTO_INCREMENT, username VARCHAR(80) NOT NULL UNIQUE, password_hash VARCHAR(200) NOT NULL, active TINYINT NOT NULL DEFAULT 1, created BIGINT NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4')
        c.execute('CREATE TABLE IF NOT EXISTS sessions (token_hash CHAR(64) PRIMARY KEY,csrf VARCHAR(128) NOT NULL,expires BIGINT NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4')
        c.execute('CREATE TABLE IF NOT EXISTS orders (id BIGINT PRIMARY KEY AUTO_INCREMENT,items LONGTEXT NOT NULL,total DECIMAL(12,2) NOT NULL,customer VARCHAR(100) NOT NULL,phone VARCHAR(30) NOT NULL,status VARCHAR(30) NOT NULL DEFAULT "Pendiente",created BIGINT NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4')
        
        if not c.execute('SELECT 1 FROM admin_users LIMIT 1').fetchone():
            pw=os.environ.get('ADMIN_PASSWORD','')
            username=os.environ.get('ADMIN_USERNAME','admin').strip()
            if len(pw)<12 or not re.fullmatch(r'[A-Za-z0-9_.-]{3,80}',username):
                raise SystemExit('Configura ADMIN_USERNAME (3+ caracteres) y ADMIN_PASSWORD (12+ caracteres) antes de iniciar.')
            salt=secrets.token_hex(16)
            digest=hashlib.scrypt(pw.encode(),salt=bytes.fromhex(salt),n=2**14,r=8,p=1).hex()
            c.execute('INSERT INTO admin_users(username,password_hash,created) VALUES(%s,%s,%s)',(username,salt+':'+digest,int(time.time())))
        
        if not c.execute('SELECT 1 FROM settings WHERE `key`="whatsapp"').fetchone():
            c.execute('INSERT INTO settings VALUES (%s,%s)',('whatsapp',os.environ.get('WHATSAPP_NUMBER','')))

DUMMY_HASH='00'*16+':'+'00'*64

def setting(c,k):
    row=c.execute('SELECT value FROM settings WHERE `key`=%s',(k,)).fetchone();return row['value'] if row else ''

def valid_image(s):return not s or (len(s)<1500 and (s.startswith('https://') or s.startswith('http://')))

class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args):pass
    def send(self,code,obj,cookie=None):
        b=json.dumps(obj,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' https: http: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers();self.wfile.write(b)

    def readjson(self):
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n>100000 or n<0:raise ValueError()
            return json.loads(self.rfile.read(n))
        except Exception:return None

    def auth(self,csrf=False):
        cookie=SimpleCookie()
        try:cookie.load(self.headers.get('Cookie',''))
        except Exception:return False
        token=cookie.get('cards_session')
        if not token:return False
        with conn() as c:r=c.execute('SELECT csrf,expires FROM sessions WHERE token_hash=%s',(hashlib.sha256(token.value.encode()).hexdigest(),)).fetchone()
        return bool(r and r['expires']>time.time() and (not csrf or hmac.compare_digest(r['csrf'],self.headers.get('X-CSRF-Token',''))))

    def do_GET(self):
        p=urlparse(self.path).path
        if p=='/api/products':
            with conn() as c:rows=[dict(r) for r in c.execute('SELECT * FROM products ORDER BY featured DESC,id DESC')]
            return self.send(200,{'products':[{**r,'price':float(r['price'])} for r in rows]})
        if p=='/api/config':
            with conn() as c:number=setting(c,'whatsapp')
            return self.send(200,{'whatsapp':number})
        if p=='/api/admin/session':
            if not self.auth():return self.send(401,{'error':'No autorizado'})
            cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''));token=cookie['cards_session'].value
            with conn() as c:r=c.execute('SELECT csrf FROM sessions WHERE token_hash=%s',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            return self.send(200,{'csrf':r['csrf']})
        if p=='/api/admin/orders':
            if not self.auth():return self.send(401,{'error':'No autorizado'})
            with conn() as c:orders=[dict(r) for r in c.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 300')]
            return self.send(200,{'orders':[{**r,'total':float(r['total'])} for r in orders]})
        if p in ('/','/index.html'):p='/index.html'
        if p not in ('/index.html','/style.css','/app.js'):return self.send(404,{'error':'No encontrado'})
        f=ROOT/'static'/p.lstrip('/');b=f.read_bytes();self.send_response(200);self.send_header('Content-Type',{'html':'text/html; charset=utf-8','css':'text/css; charset=utf-8','js':'application/javascript; charset=utf-8'}[f.suffix[1:]]);self.send_header('Content-Length',str(len(b)));self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.end_headers();self.wfile.write(b)

    def do_POST(self):
        p=urlparse(self.path).path;d=self.readjson()
        if not isinstance(d,dict):return self.send(400,{'error':'Datos inválidos'})
        if p=='/api/admin/login':
            ip=self.client_address[0];now=time.time()
            with lock:
                a=[t for t in attempts.get(ip,[]) if now-t<900];attempts[ip]=a
                if len(a)>=8:return self.send(429,{'error':'Demasiados intentos. Prueba en 15 minutos.'})
            username=str(d.get('username','')).strip()[:80]
            with conn() as c:account=c.execute('SELECT password_hash FROM admin_users WHERE username=%s AND active=1',(username,)).fetchone()
            stored=account['password_hash'] if account else DUMMY_HASH
            salt,digest=stored.split(':');candidate=hashlib.scrypt(str(d.get('password','')).encode()[:256],salt=bytes.fromhex(salt),n=2**14,r=8,p=1).hex()
            if not account or not hmac.compare_digest(candidate,digest):
                with lock:attempts[ip].append(now)
                return self.send(401,{'error':'Contraseña incorrecta'})
            with lock:attempts.pop(ip,None)
            token=secrets.token_urlsafe(40);csrf=secrets.token_urlsafe(32)
            with conn() as c:c.execute('INSERT INTO sessions VALUES(%s,%s,%s)',(hashlib.sha256(token.encode()).hexdigest(),csrf,int(now)+28800))
            return self.send(200,{'csrf':csrf},'cards_session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'+('; Secure' if HTTPS else ''))
        
        if p=='/api/orders':
            customer=str(d.get('customer','')).strip()[:100];phone=str(d.get('phone','')).strip()[:30];items=d.get('items',[])
            if not customer or not re.fullmatch(r'[+\d ()-]{7,30}',phone) or not isinstance(items,list) or not 1<=len(items)<=40:return self.send(400,{'error':'Revisa tus datos y el carrito'})
            quantities={}
            for item in items:
                try:pid=int(item['id']);qty=int(item['qty'])
                except Exception:return self.send(400,{'error':'Producto inválido'})
                if qty<1 or qty>100:return self.send(400,{'error':'Cantidad inválida'})
                quantities[pid]=quantities.get(pid,0)+qty
            with lock:
                with conn() as c:
                    summary=[];total=0
                    for pid,qty in quantities.items():
                        r=c.execute('SELECT * FROM products WHERE id=%s FOR UPDATE',(pid,)).fetchone()
                        if not r or r['stock']<qty:c.db.rollback();return self.send(409,{'error':'Stock insuficiente. Actualiza el carrito.'})
                        subtotal=round(float(r['price'])*qty,2);total+=subtotal;summary.append({'name':r['name'],'qty':qty,'price':float(r['price'])});c.execute('UPDATE products SET stock=stock-%s WHERE id=%s',(qty,pid))
                    total=round(total,2);cur=c.execute('INSERT INTO orders(items,total,customer,phone,created) VALUES(%s,%s,%s,%s,%s)',(json.dumps(summary,ensure_ascii=False),total,customer,phone,int(time.time())));oid=c.lastrowid;number=setting(c,'whatsapp')
            return self.send(200,{'id':oid,'total':total,'items':summary,'whatsapp':number})
        
        if not self.auth(csrf=True):return self.send(403,{'error':'Acceso denegado o sesión vencida'})
        
        if p=='/api/admin/logout':
            cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''));t=cookie.get('cards_session')
            if t:
                with conn() as c:c.execute('DELETE FROM sessions WHERE token_hash=%s',(hashlib.sha256(t.value.encode()).hexdigest(),))
            return self.send(200,{'ok':True},'cards_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
        
        if p=='/api/admin/config':
            number=re.sub(r'\D','',str(d.get('whatsapp','')))
            if not 10<=len(number)<=15:return self.send(400,{'error':'Ingresa WhatsApp con código de país, ejemplo 51999999999'})
            with conn() as c:c.execute('INSERT INTO settings VALUES(%s,%s) ON DUPLICATE KEY UPDATE value=VALUES(value)',('whatsapp',number))
            return self.send(200,{'ok':True})
        
        if p=='/api/admin/products':
            try:
                name=str(d['name']).strip()[:120];collection=str(d.get('collection','')).strip()[:100];rarity=str(d.get('rarity','')).strip()[:80];price=round(float(d['price']),2);stock=int(d['stock']);img=str(d.get('image','')).strip();description=str(d.get('description','')).strip()[:1000];featured=int(bool(d.get('featured')));pid=int(d.get('id') or 0)
                if not name or not 0<=price<=1000000 or not 0<=stock<=1000000 or not valid_image(img):raise ValueError()
            except Exception:return self.send(400,{'error':'Datos de producto inválidos'})
            with conn() as c:
                if pid:
                    c.execute('UPDATE products SET name=%s,collection=%s,rarity=%s,price=%s,stock=%s,image=%s,description=%s,featured=%s WHERE id=%s',(name,collection,rarity,price,stock,img,description,featured,pid))
                    if not c.rowcount:return self.send(404,{'error':'Producto no encontrado'})
                else:
                    c.execute('INSERT INTO products(name,collection,rarity,price,stock,image,description,featured,created) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',(name,collection,rarity,price,stock,img,description,featured,int(time.time())))
                    pid=c.lastrowid
            return self.send(200,{'ok':True,'id':pid})
        
        if p=='/api/admin/products/delete':
            try: pid=int(d.get('id',0))
            except (TypeError,ValueError):return self.send(400,{'error':'ID inválido'})
            with conn() as c:c.execute('DELETE FROM products WHERE id=%s',(pid,))
            return self.send(200,{'ok':True})
        
        if p=='/api/admin/orders/status':
            if d.get('status') not in ('Pendiente','Confirmado','Enviado','Cancelado'):return self.send(400,{'error':'Estado inválido'})
            try: oid=int(d.get('id',0))
            except (TypeError,ValueError):return self.send(400,{'error':'ID inválido'})
            with conn() as c:c.execute('UPDATE orders SET status=%s WHERE id=%s',(d['status'],oid))
            return self.send(200,{'ok':True})
        
        return self.send(404,{'error':'Ruta no encontrada'})

if __name__=='__main__':
    init();print(f'Cards TCG disponible en http://localhost:{PORT}');ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()