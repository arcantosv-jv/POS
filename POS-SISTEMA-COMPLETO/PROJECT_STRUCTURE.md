# 📁 Estructura del Proyecto POS Sistema

```
pos-system/
│
├── 🔧 CONFIGURACIÓN
│   ├── app.py                      # Aplicación principal Flask
│   ├── config.py                   # Configuración de entornos
│   ├── models.py                   # Modelos de base de datos
│   ├── requirements.txt             # Dependencias Python
│   ├── .env.example                # Variables de entorno (ejemplo)
│   ├── .gitignore                  # Archivos a ignorar en Git
│   └── gunicorn_config.py          # Configuración de Gunicorn
│
├── 🛣️ RUTAS (Backend)
│   ├── routes_auth.py              # Autenticación
│   ├── routes_admin.py             # Administración (usuarios, sucursales)
│   ├── routes_productos.py         # Gestión de productos
│   ├── routes_inventario.py        # Gestión de inventario
│   ├── routes_ventas.py            # Punto de venta
│   ├── routes_reportes.py          # Reportes y estadísticas
│   └── routes_importar.py          # Importación de datos
│
├── 🐳 DOCKER
│   ├── Dockerfile                  # Imagen Docker
│   ├── docker-compose.yml          # Orquestación de containers
│   └── docker-entrypoint.sh        # Script de entrada
│
├── 🌐 FRONTEND
│   └── static/
│       ├── index.html              # Interfaz principal (SPA)
│       ├── app.js                  # Lógica Vue.js
│       └── components.js           # Componentes Vue.js
│
├── 📚 DATABASE
│   └── migrations/
│       ├── alembic.ini             # Configuración Alembic
│       ├── env.py                  # Ambiente de migraciones
│       └── versions/
│           └── 001_initial_migration.py  # Migración inicial
│
├── 📖 DOCUMENTACIÓN
│   ├── README.md                   # Documentación completa
│   └── QUICKSTART.md               # Guía de inicio rápido
│
├── 🔨 SCRIPTS DE UTILIDAD
│   ├── init_db.sh                  # Inicializar BD (Linux/Mac)
│   ├── init_db.bat                 # Inicializar BD (Windows)
│   ├── backup_db.sh                # Hacer backup de BD
│   └── restore_db.sh               # Restaurar backup
│
└── 📋 INFORMACIÓN
    ├── PROJECT_STRUCTURE.md        # Este archivo
    └── CHANGELOG.md                # Historial de cambios
```

## 📦 Archivos Principales

### Backend (Python/Flask)

| Archivo | Descripción |
|---------|-------------|
| `app.py` | Aplicación Flask principal, carga todas las rutas |
| `config.py` | Configuración (desarrollo, producción, testing) |
| `models.py` | Modelos SQLAlchemy (User, Producto, Venta, etc) |
| `routes_*.py` | Endpoints de la API (auth, productos, ventas, reportes) |

### Frontend (HTML/Vue.js)

| Archivo | Descripción |
|---------|-------------|
| `static/index.html` | HTML principal, incluye estilos CSS |
| `static/app.js` | Lógica principal de Vue.js |
| `static/components.js` | Componentes reutilizables (Ventas, Productos, Reportes) |

### Docker

| Archivo | Descripción |
|---------|-------------|
| `Dockerfile` | Define la imagen Docker |
| `docker-compose.yml` | Orquestación (Flask + PostgreSQL) |
| `docker-entrypoint.sh` | Script que ejecuta migraciones antes de iniciar |

### Base de Datos

| Archivo | Descripción |
|---------|-------------|
| `migrations/env.py` | Ambiente de Alembic |
| `migrations/versions/001_initial_migration.py` | Crea todas las tablas |

## 🗄️ Estructura de la Base de Datos

```sql
-- Usuarios y Autenticación
- users (id, username, email, password_hash, role, sucursal_id, is_active)

-- Configuración del Negocio
- sucursales (id, nombre, direccion, telefono, ciudad, is_active)

-- Catálogo de Productos
- categorias (id, nombre, descripcion, is_active)
- subcategorias (id, nombre, categoria_id, is_active)
- productos (id, codigo, nombre, precio, impuesto, subcategoria_id, codigo_barras, is_active)

-- Inventario
- stocks (id, producto_id, sucursal_id, cantidad, cantidad_minima)
- entradas_inventario (id, producto_id, sucursal_id, cantidad, numero_entrada, created_at)

-- Ventas
- ventas (id, numero_venta, sucursal_id, cajero_id, total, total_impuestos, forma_pago, created_at)
- detalles_venta (id, venta_id, producto_id, cantidad, precio_unitario, subtotal)
```

## 🔌 Endpoints de la API

### Autenticación
- `POST /api/auth/login` - Login
- `POST /api/auth/register` - Registro (solo admin)
- `GET /api/auth/profile` - Perfil del usuario

### Productos
- `GET /api/productos` - Listar productos
- `POST /api/productos` - Crear producto
- `GET /api/productos/buscar?q=term` - Buscar productos
- `POST /api/productos/importar` - Importar desde CSV

### Ventas
- `POST /api/ventas` - Crear venta
- `GET /api/ventas` - Listar ventas
- `GET /api/ventas/<id>/ticket` - Obtener ticket

### Inventario
- `GET /api/inventario/stock/<sucursal_id>` - Stock de sucursal
- `POST /api/inventario/entrada` - Registrar entrada

### Reportes
- `GET /api/reportes/ventas-diarias` - Reporte diario
- `GET /api/reportes/ventas-mensuales` - Reporte mensual
- `GET /api/reportes/consolidado-sucursales` - Consolidado

### Administración
- `GET /api/admin/sucursales` - Listar sucursales
- `GET /api/admin/usuarios` - Listar usuarios

## 🚀 Comandos Útiles

### Docker
```bash
docker-compose up -d              # Iniciar
docker-compose down               # Detener
docker-compose logs -f app        # Ver logs
docker-compose exec db psql ...   # Acceder a BD
```

### Local
```bash
python -m venv venv              # Crear entorno
source venv/bin/activate          # Activar entorno
pip install -r requirements.txt   # Instalar dependencias
flask db upgrade                  # Ejecutar migraciones
python app.py                     # Iniciar servidor
```

### Base de Datos
```bash
bash backup_db.sh                 # Hacer backup
bash restore_db.sh backups/file   # Restaurar backup
psql -U pos_user -d pos_db        # Acceder a BD
```

## 📊 Roles y Permisos

### Admin
- ✅ Ver dashboard
- ✅ Crear/editar productos
- ✅ Importar productos en masa
- ✅ Gestionar inventario
- ✅ Ver reportes consolidados
- ✅ Crear usuarios
- ✅ Gestionar sucursales

### Empleado
- ✅ Registrar ventas
- ✅ Buscar productos
- ✅ Generar tickets
- ✅ Ver ventas de su sucursal
- ❌ No puede crear productos
- ❌ No puede ver otras sucursales

## 🔐 Seguridad

- JWT para autenticación
- Hashing bcrypt para contraseñas
- CORS habilitado
- Control de acceso por rol
- Variables de entorno sensibles

## 💾 Migraciones de BD

Las migraciones se ejecutan automáticamente:
- Con Docker: Al iniciar el container
- Localmente: `flask db upgrade`

Para crear nuevas migraciones:
```bash
flask db migrate -m "Descripción del cambio"
flask db upgrade
```

## 📦 Dependencias Principales

- **Flask** - Framework web
- **SQLAlchemy** - ORM
- **Flask-JWT-Extended** - Autenticación JWT
- **PostgreSQL** - Base de datos
- **Vue.js** - Frontend reactivo
- **Gunicorn** - Servidor WSGI producción

## ✅ Checklist de Despliegue

Antes de producción:
- [ ] Cambiar credenciales por defecto
- [ ] Configurar variables de entorno seguras
- [ ] Hacer backup de BD
- [ ] Configurar HTTPS
- [ ] Revisar logs
- [ ] Pruebas de carga
- [ ] Plan de disaster recovery

---

**Última actualización**: Mayo 2026  
**Versión**: 1.0.0
