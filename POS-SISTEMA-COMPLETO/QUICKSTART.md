# 🚀 Guía de Inicio Rápido - POS Sistema

## ⚡ Inicio en 5 minutos

### Opción 1: CON DOCKER (Más fácil ✨)

```bash
# 1. Descargar el proyecto
git clone <tu-repo>
cd pos-system

# 2. Iniciar con Docker
docker-compose up -d

# 3. Listo! Accede a http://localhost:5000
```

**Credenciales:**
- Usuario: `admin`
- Contraseña: `admin123`

---

### Opción 2: SIN DOCKER (Local)

#### En Windows:

```bash
# 1. Descargar Python 3.11+ desde python.org
# 2. Descargar PostgreSQL desde postgresql.org

# 3. Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Crear archivo .env
copy .env.example .env

# 6. Editar .env con tus datos de PostgreSQL
notepad .env

# 7. Inicializar base de datos
init_db.bat

# 8. Ejecutar aplicación
python app.py
```

#### En Linux/Mac:

```bash
# 1. Instalar dependencias del sistema
sudo apt-get install python3.11 postgresql postgresql-contrib

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias Python
pip install -r requirements.txt

# 4. Crear archivo .env
cp .env.example .env

# 5. Editar .env
nano .env

# 6. Inicializar base de datos
bash init_db.sh

# 7. Ejecutar aplicación
python app.py
```

---

## 🎯 Primeros Pasos

### 1️⃣ Acceder a la aplicación
- URL: `http://localhost:5000`
- Usuario: `admin`
- Contraseña: `admin123`

### 2️⃣ Crear tu primer empleado

1. Ve a **Usuarios** (solo visible si eres admin)
2. Haz clic en **+ Nuevo Usuario**
3. Completa los datos:
   - Usuario: `empleado1`
   - Email: `empleado1@pos.local`
   - Contraseña: segura
   - Rol: Empleado
   - Sucursal: Sucursal Centro
4. Haz clic en **Guardar Usuario**

### 3️⃣ Importar productos

1. Ve a **Productos**
2. Haz clic en **📤 Importar Excel/CSV**
3. Selecciona tu archivo CSV
4. Selecciona la sucursal
5. Haz clic en **✓ Importar Productos**

**Formato del CSV esperado:**
```csv
Handle,REF,Nombre,Categoria,Descripción,Precio [Sucursal],En inventario [Sucursal]
mica-iphone-15,001,Mica iPhone 15,Mica,Protector,50.00,10
funda-samsung,002,Funda Samsung,Funda,Protector,30.00,5
```

### 4️⃣ Primera venta

1. Cierra sesión como admin
2. Inicia sesión como `empleado1`
3. Ve a **Ventas**
4. Busca un producto
5. Haz clic en el producto para agregarlo
6. Ajusta cantidad si necesitas
7. Selecciona forma de pago
8. Haz clic en **✓ Cobrar**
9. Imprime el ticket

---

## 📊 Funciones principales

### 👨‍💼 Como Admin puedes:

| Función | Ubicación |
|---------|-----------|
| Ver Dashboard | Dashboard |
| Gestionar Productos | Productos |
| Importar productos en masa | Productos → Importar Excel/CSV |
| Registrar entrada de stock | Inventario → Registrar Entrada |
| Ver stock por sucursal | Inventario |
| Generar reportes | Reportes |
| Crear usuarios | Usuarios |
| Gestionar sucursales | Admin (no visible en menú, vía API) |

### 👤 Como Empleado puedes:

| Función | Ubicación |
|---------|-----------|
| Registrar ventas | Ventas |
| Buscar productos | Ventas |
| Ver carrito | Ventas |
| Imprimir tickets | Ventas |

---

## 🔍 Búsqueda de Productos

En el módulo de **Ventas**, puedes buscar productos por:

- **Nombre**: "Mica", "Funda", "Audífono"
- **Código**: "001", "SKU-123"
- **Código de barras**: Escanea directamente

La búsqueda es **parcial**, así que si escribes "moto" te mostrará "Mica Moto G55", "Funda Moto G60", etc.

---

## 📱 Uso desde Móvil/Tablet

La aplicación está optimizada para móvil:

1. Abre en navegador: `http://tu-servidor:5000`
2. La interfaz se adapta automáticamente
3. Puedes usar como app: 
   - **Android**: Menú → Instalar app
   - **iOS**: Compartir → Añadir a pantalla de inicio

---

## 🆘 Problemas Comunes

### "No puedo conectar a la base de datos"

**Docker:**
```bash
docker-compose logs db
# Reinicia los containers
docker-compose down
docker-compose up -d
```

**Local:**
- Verifica que PostgreSQL está corriendo
- Comprueba credenciales en `.env`
- Ejecuta: `psql -U postgres -d pos_db`

### "Puerto 5000 ya está en uso"

**Windows:**
```bash
netstat -ano | findstr :5000
taskkill /PID <numero> /F
```

**Linux/Mac:**
```bash
lsof -i :5000
kill -9 <PID>
```

### "No aparecen mis productos importados"

1. Verifica el formato del CSV
2. Comprueba que la sucursal está correcta
3. Recarga la página (F5)
4. Revisa la consola (F12) para errores

### "Olvidé la contraseña del admin"

Reinicializa la base de datos:

**Docker:**
```bash
docker-compose down -v
docker-compose up -d
```

**Local:**
```bash
rm -rf instance/
rm -rf migrations/
python app.py
init_db.sh (o init_db.bat en Windows)
```

---

## 🚀 Desplegar a Producción

### En Railway (Recomendado)

1. Crea cuenta en [railway.app](https://railway.app)
2. Conecta tu repositorio GitHub
3. Agrega plugin PostgreSQL
4. Configura variables de entorno:
   ```
   FLASK_ENV=production
   SECRET_KEY=<algo-muy-seguro>
   JWT_SECRET_KEY=<algo-muy-seguro>
   DATABASE_URL=<la-que-genera-railway>
   ```
5. Deploy automático cuando hagas push

### En tu servidor (VPS)

```bash
# 1. SSH a tu servidor
ssh user@tu-servidor.com

# 2. Clona el proyecto
git clone <tu-repo>
cd pos-system

# 3. Instala dependencias del sistema
sudo apt-get update
sudo apt-get install python3.11 postgresql nginx

# 4. Crea entorno virtual y instala paquetes
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Configura .env
cp .env.example .env
nano .env  # Edita con tus datos

# 6. Inicializa BD
flask db upgrade

# 7. Ejecuta con systemd (recomendado)
sudo nano /etc/systemd/system/pos.service

# Contenido del archivo:
[Unit]
Description=POS Sistema
After=network.target

[Service]
User=www-data
WorkingDirectory=/home/user/pos-system
Environment="PATH=/home/user/pos-system/venv/bin"
ExecStart=/home/user/pos-system/venv/bin/gunicorn --bind 0.0.0.0:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target

# 8. Inicia el servicio
sudo systemctl start pos
sudo systemctl enable pos

# 9. Configura Nginx como proxy
sudo nano /etc/nginx/sites-available/pos

# Contenido:
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# 10. Habilita sitio Nginx
sudo ln -s /etc/nginx/sites-available/pos /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

---

## 📞 Soporte

- 📖 Lee el [README.md](README.md) completo
- 🐛 Revisa los logs: `docker logs pos_app` (Docker)
- 💻 Abre consola del navegador: F12
- 📧 Contacta al equipo de desarrollo

---

**¡Listo! 🎉 Ya tienes tu POS Sistema funcionando**

Próximos pasos:
1. ✅ Crear empleados
2. ✅ Importar productos
3. ✅ Registrar primera venta
4. ✅ Generar reportes
5. ✅ Hacer backup de datos

¡Gracias por usar POS Sistema!
