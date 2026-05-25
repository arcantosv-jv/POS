# 🚀 Instalación POS Sistema

## ✅ Verificación Previa

Antes de instalar, verifica que tengas:

### Con Docker (Recomendado)
- [ ] Docker instalado (`docker --version`)
- [ ] Docker Compose instalado (`docker-compose --version`)

### Sin Docker
- [ ] Python 3.11+ (`python --version`)
- [ ] PostgreSQL 12+ (`psql --version`)
- [ ] pip (`pip --version`)

---

## 📋 Opción 1: Instalación CON DOCKER (5 minutos)

### Paso 1: Preparar el proyecto

```bash
# 1. Descargar o clonar el proyecto
cd pos-system

# 2. Crear archivo .env
cp .env.example .env

# 3. (Opcional) Editar .env si necesitas cambiar contraseñas
# Nota: Los valores por defecto funcionan bien
```

### Paso 2: Iniciar con Docker

```bash
# Construir e iniciar containers
docker-compose up -d

# Esperar 10 segundos a que se inicialice

# Verificar que todo está corriendo
docker-compose ps

# Deberías ver 2 containers: pos_app y pos_db
```

### Paso 3: Acceder a la aplicación

- **URL**: http://localhost:5000
- **Usuario**: admin
- **Contraseña**: admin123

### Troubleshooting Docker

**Error: "Cannot connect to Docker daemon"**
```bash
# Windows/Mac: Abre Docker Desktop
# Linux: Inicia el servicio de Docker
sudo systemctl start docker
```

**Error: "Port 5000 already in use"**
```bash
# Cambiar puerto en docker-compose.yml
# Línea: ports: - "8000:5000"  # Cambiar 5000 por otro puerto
docker-compose up -d
```

**Ver logs**
```bash
docker-compose logs -f app
```

---

## 📋 Opción 2: Instalación SIN DOCKER (Local)

### Windows

#### Requisitos
1. Instala Python 3.11+ desde [python.org](https://python.org)
   - ✅ Marca "Add Python to PATH" durante la instalación
2. Instala PostgreSQL desde [postgresql.org](https://postgresql.org)

#### Pasos de Instalación

```bash
# 1. Abre PowerShell o CMD

# 2. Navega a la carpeta del proyecto
cd C:\ruta\a\pos-system

# 3. Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Crear archivo .env
copy .env.example .env

# 6. Editar .env (Nota: Opcional, valores por defecto funcionan)
# Abre .env con Notepad y verifica las credenciales de PostgreSQL
notepad .env

# 7. Crear base de datos en PostgreSQL
# Abre pgAdmin (viene con PostgreSQL)
# Crea una BD llamada "pos_db"
# Usuario: pos_user (crear si no existe)

# 8. Inicializar BD
init_db.bat

# 9. Ejecutar servidor
python app.py
```

**Acceso**: http://localhost:5000

---

### Linux / Mac

#### Requisitos (Ubuntu/Debian)

```bash
# Instalar dependencias del sistema
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv python3-pip postgresql postgresql-contrib

# Iniciar PostgreSQL
sudo systemctl start postgresql
```

#### Pasos de Instalación

```bash
# 1. Navega a la carpeta del proyecto
cd ~/pos-system

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Crear archivo .env
cp .env.example .env

# 5. Crear usuario y BD en PostgreSQL
sudo -u postgres psql << EOF
CREATE USER pos_user WITH PASSWORD 'pos_secure_password_123';
ALTER ROLE pos_user SET client_encoding TO 'utf8';
ALTER ROLE pos_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE pos_user SET default_transaction_deferrable TO on;
ALTER ROLE pos_user SET timezone TO 'UTC';
CREATE DATABASE pos_db OWNER pos_user;
GRANT ALL PRIVILEGES ON DATABASE pos_db TO pos_user;
EOF

# 6. Inicializar BD
bash init_db.sh

# 7. Ejecutar servidor
python app.py
```

**Acceso**: http://localhost:5000

---

## ✅ Verificación Post-Instalación

### 1. Verificar acceso web
```bash
curl http://localhost:5000
# Deberías recibir una respuesta JSON
```

### 2. Probar login
- URL: http://localhost:5000
- Usuario: admin
- Contraseña: admin123

### 3. Crear sucursal (opcional)
En el panel admin, puedes crear sucursales adicionales

### 4. Crear un empleado (opcional)
En Admin → Usuarios, crea un empleado para probar

### 5. Hacer una venta de prueba
1. Cierra sesión como admin
2. Inicia sesión como empleado
3. Ve a Ventas
4. Busca un producto
5. Agrega al carrito y registra venta

---

## 🔧 Configuración Recomendada

### Cambiar credenciales por defecto

**En producción**, SIEMPRE cambia las credenciales:

#### 1. Cambiar contraseña del admin

```bash
# Con Docker
docker-compose exec app flask shell
>>> from app import create_app, db
>>> from models import User
>>> app = create_app()
>>> with app.app_context():
...     user = User.query.filter_by(username='admin').first()
...     user.set_password('nueva_contraseña_segura')
...     db.session.commit()
>>> exit()

# Sin Docker (local)
# Abre una terminal en el proyecto
flask shell
>>> from models import User
>>> user = User.query.filter_by(username='admin').first()
>>> user.set_password('nueva_contraseña_segura')
>>> db.session.commit()
>>> exit()
```

#### 2. Cambiar variables de entorno

Edita `.env`:
```
SECRET_KEY=algo-muy-seguro-y-largo
JWT_SECRET_KEY=otro-algo-muy-seguro-y-largo
DB_PASSWORD=tu-nueva-contraseña-segura
```

Reinicia la aplicación para que los cambios tomen efecto.

---

## 📊 Importar Primeros Datos

### Importar Productos

1. Prepara un archivo CSV con este formato:
```csv
Handle,REF,Nombre,Categoria,Descripción,Precio [Sucursal Centro],En inventario [Sucursal Centro]
mica-001,001,Mica iPhone 15,Mica,Protector,50.00,10
funda-001,002,Funda Samsung,Funda,Protector,30.00,5
```

2. En Productos → Importar Excel/CSV
3. Selecciona el archivo y sucursal
4. Haz clic en Importar

---

## 🛑 Detener la Aplicación

### Con Docker
```bash
docker-compose down
```

### Sin Docker
```bash
# Presiona Ctrl + C en la terminal
# O en otra terminal:
pkill -f "python app.py"
```

---

## 🔄 Reiniciar/Resetear

### Limpiar todo (reset completo)

**Con Docker:**
```bash
docker-compose down -v
docker-compose up -d
```

**Sin Docker:**
```bash
# Elimina la BD
dropdb -U pos_user pos_db
createdb -U pos_user pos_db

# Reinicia el servidor
python app.py
```

---

## 📞 Problemas Comunes y Soluciones

### "No puedo conectar a la aplicación (ConnectionRefused)"

**Con Docker:**
```bash
docker-compose logs app
# Busca errores y comparte el log
```

**Sin Docker:**
```bash
# Asegúrate de que el servidor está corriendo
# Verifica que usas http://localhost:5000 (no https)
# Intenta en otra pestaña del navegador
```

### "Error de autenticación a BD"

**Con Docker:**
```bash
# Verifica que DB_PASSWORD en docker-compose.yml coincide con .env
docker-compose down -v
docker-compose up -d
```

**Sin Docker:**
```bash
# Verifica credenciales en .env
# Prueba conectar directamente:
psql -U pos_user -d pos_db -h localhost
# Ingresa la contraseña cuando pida
```

### "Puerto ya está en uso"

**Con Docker:**
```bash
# Cambia el puerto en docker-compose.yml
# Línea: ports: - "8000:5000"
docker-compose up -d
```

**Sin Docker:**
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <numero> /F

# Linux/Mac
lsof -i :5000
kill -9 <PID>
```

### "Módulo de Python no encontrado"

```bash
# Reinstala dependencias
pip install -r requirements.txt --force-reinstall
```

---

## 📚 Siguientes Pasos

1. ✅ Lee la [Guía de Inicio Rápido](QUICKSTART.md)
2. ✅ Crea usuarios adicionales
3. ✅ Importa tu catálogo de productos
4. ✅ Registra tu primera venta
5. ✅ Genera reportes

---

## 🆘 ¿Aún tienes problemas?

1. Revisa los logs:
   - Docker: `docker-compose logs app`
   - Local: Revisa la consola donde ejecutaste `python app.py`

2. Abre la consola del navegador (F12) y revisa errores

3. Intenta desactivar extensiones del navegador

4. Prueba en incógnito/privado

---

**¡Listo! Tu POS Sistema está configurado. 🎉**

Para más ayuda, consulta [README.md](README.md) o [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
