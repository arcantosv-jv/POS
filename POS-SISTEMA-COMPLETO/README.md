# POS Sistema - Punto de Venta

Sistema completo de Punto de Venta (POS) desarrollado con Flask (backend) y Vue.js (frontend), diseñado para gestionar múltiples sucursales con usuarios diferenciados y funcionalidades avanzadas de inventario y reportes.

## 🎯 Características

### 🔐 Autenticación y Autorización
- Login seguro con JWT
- Roles: Admin y Empleado
- Sesiones persistentes
- Control de acceso por sucursal

### 💰 Módulo de Ventas
- Búsqueda rápida de productos (por nombre, código, código de barras)
- Carrito de compra interactivo
- Cálculo automático de impuestos
- Múltiples formas de pago (efectivo, tarjeta, transferencia, mixto)
- Generación de tickets imprimibles
- Historial de transacciones

### 📦 Gestión de Productos
- Catálogo completo de productos
- Categorías y subcategorías
- Importación masiva desde Excel/CSV
- Códigos de barras
- Configuración de impuestos por producto
- Búsqueda avanzada

### 📊 Inventario y Stock
- Control de stock por sucursal
- Registro de entradas de inventario
- Alertas de stock bajo
- Ajustes manuales de cantidad
- Historial de movimientos

### 📈 Reportes y Análisis
- Reporte diario de ventas
- Reporte mensual y anual
- Consolidado por sucursal (solo admin)
- Análisis de productos más vendidos
- Métricas de desempeño

### 👥 Gestión de Usuarios (Admin)
- Crear empleados por sucursal
- Roles diferenciados
- Control de acceso por sucursal
- Historial de actividades

### 🏪 Múltiples Sucursales
- Gestión de sucursales
- Stock independiente por sucursal
- Reportes consolidados
- Asignación de usuarios a sucursales

## 🚀 Instalación Rápida

### Opción 1: Con Docker (Recomendado)

```bash
# Clonar o descargar el proyecto
cd pos-system

# Crear archivo .env
cp .env.example .env

# Editar .env si es necesario (contraseñas, etc)
nano .env

# Construir e iniciar containers
docker-compose up -d

# La aplicación estará en http://localhost:5000
```

### Opción 2: Local (Sin Docker)

#### Requisitos
- Python 3.11+
- PostgreSQL 12+
- pip

#### Pasos

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Crear archivo .env
cp .env.example .env

# 4. Configurar base de datos
# Editar DATABASE_URL en .env con tus credenciales de PostgreSQL

# 5. Crear tablas
flask db upgrade

# 6. Ejecutar servidor
python app.py

# La aplicación estará en http://localhost:5000
```

## 📝 Credenciales por Defecto

```
Usuario: admin
Contraseña: admin123
```

⚠️ **IMPORTANTE**: Cambiar estas credenciales en producción

## 🛠️ Configuración

### Variables de Entorno (.env)

```env
# Base de Datos
DB_USER=pos_user
DB_PASSWORD=pos_secure_password_123
DB_NAME=pos_db
DB_HOST=db              # 'db' para Docker, 'localhost' para local
DB_PORT=5432

# Flask
FLASK_ENV=production
SECRET_KEY=tu-clave-secreta-aqui
JWT_SECRET_KEY=tu-jwt-secret-aqui

# Seguridad
DEBUG=False
```

## 📱 Uso de la Aplicación

### Para Empleados (Punto de Venta)

1. **Login** con tu usuario
2. **Buscar productos** por nombre, código o código de barras
3. **Agregar productos al carrito**
4. **Ajustar cantidades** si es necesario
5. **Seleccionar forma de pago**
6. **Registrar venta**
7. **Imprimir ticket**

### Para Administrador

#### Productos
- Crear nuevos productos
- Importar masivamente desde Excel/CSV
- Editar información
- Gestionar categorías y subcategorías

#### Inventario
- Registrar entradas de stock
- Ver stock actual por sucursal
- Recibir alertas de stock bajo
- Ajustar cantidades manualmente

#### Reportes
- Generar reportes diarios, mensuales y anuales
- Ver consolidados por sucursal
- Análisis de productos más vendidos
- Métricas de desempeño

#### Usuarios
- Crear empleados
- Asignar a sucursales
- Cambiar roles
- Desactivar usuarios

## 📤 Importar Productos desde Excel/CSV

### Formato del archivo

El archivo debe tener las siguientes columnas (como mínimo):

```
Handle, REF, Nombre, Categoria, Descripción, ..., Precio [Sucursal], En inventario [Sucursal]
```

### Pasos

1. Ir a **Productos** → **Importar Excel/CSV**
2. Seleccionar archivo CSV
3. Seleccionar sucursal
4. Hacer clic en **Importar Productos**

### Ejemplo de CSV

```csv
Handle,REF,Nombre,Categoria,Descripción,Precio [Motocell],En inventario [Motocell]
9d-iphone-15-plus,10956,9D iPhone 15 Plus,Mica 9D,Protector de pantalla,98.00,10
9d-samsung-a06,11003,9D Samsung A06,Mica 9D,Protector de pantalla,15.00,25
```

## 🌐 Despliegue en Railway

### Pasos

1. Crear cuenta en [Railway.app](https://railway.app)

2. Conectar repositorio de GitHub

3. En Railway:
   - Crear plugin de PostgreSQL
   - Crear servicio Web
   - Configurar variables de entorno
   
4. Variables de entorno necesarias:
   ```
   DATABASE_URL=postgresql://user:pass@host:5432/pos_db
   FLASK_ENV=production
   SECRET_KEY=tu-clave-aqui
   JWT_SECRET_KEY=tu-jwt-secret-aqui
   ```

5. Command:
   ```
   gunicorn --bind 0.0.0.0:${PORT} app:app
   ```

## 📊 Estructura del Proyecto

```
pos-system/
├── app.py                 # Aplicación principal Flask
├── models.py              # Modelos de base de datos
├── config.py              # Configuración
├── requirements.txt       # Dependencias Python
├── Dockerfile             # Configuración Docker
├── docker-compose.yml     # Orquestación Docker
├── .env.example           # Variables de entorno ejemplo
├── routes_auth.py         # Autenticación
├── routes_admin.py        # Administración
├── routes_productos.py    # Gestión de productos
├── routes_inventario.py   # Gestión de inventario
├── routes_ventas.py       # Punto de venta
├── routes_reportes.py     # Reportes
├── routes_importar.py     # Importación de datos
└── static/
    ├── index.html         # Interfaz principal
    ├── app.js             # Lógica Vue.js
    └── components.js      # Componentes Vue.js
```

## 🔧 API Endpoints

### Autenticación
- `POST /api/auth/login` - Iniciar sesión
- `POST /api/auth/register` - Registrar usuario (admin)
- `GET /api/auth/profile` - Perfil del usuario
- `POST /api/auth/change-password` - Cambiar contraseña

### Productos
- `GET /api/productos` - Listar productos
- `POST /api/productos` - Crear producto (admin)
- `GET /api/productos/buscar` - Buscar productos
- `PUT /api/productos/<id>` - Actualizar producto (admin)
- `DELETE /api/productos/<id>` - Eliminar producto (admin)

### Ventas
- `POST /api/ventas` - Registrar venta
- `GET /api/ventas` - Listar ventas
- `GET /api/ventas/<id>` - Detalle de venta
- `GET /api/ventas/<id>/ticket` - Datos para imprimir ticket

### Inventario
- `GET /api/inventario/stock/<sucursal_id>` - Stock de sucursal
- `POST /api/inventario/entrada` - Registrar entrada
- `GET /api/inventario/entradas` - Historial entradas
- `GET /api/inventario/bajo-stock/<sucursal_id>` - Productos bajo stock

### Reportes
- `GET /api/reportes/ventas-diarias` - Reporte diario
- `GET /api/reportes/ventas-mensuales` - Reporte mensual
- `GET /api/reportes/ventas-anuales` - Reporte anual
- `GET /api/reportes/productos-vendidos` - Top productos
- `GET /api/reportes/consolidado-sucursales` - Consolidado (admin)

### Administración
- `GET /api/admin/sucursales` - Listar sucursales
- `POST /api/admin/sucursales` - Crear sucursal
- `GET /api/admin/usuarios` - Listar usuarios
- `POST /api/admin/usuarios` - Crear usuario (auth/register)

## 🐛 Troubleshooting

### "Error de conexión a base de datos"
- Verificar que PostgreSQL está corriendo
- Confirmar credenciales en .env
- Verificar que la base de datos existe

### "Puerto 5000 ya está en uso"
```bash
# Linux/Mac
lsof -i :5000
kill -9 <PID>

# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### "Error importando CSV"
- Verificar que el archivo esté en formato CSV
- Confirmar que tiene las columnas requeridas
- Revisar que los datos no tengan caracteres especiales

### "No se ve el frontend"
- Limpiar caché del navegador (Ctrl+Shift+Delete)
- Verificar que static/ contiene index.html
- Revisar consola del navegador (F12) para errores

## 📞 Soporte

Para reportar bugs o solicitar features:
1. Verificar los logs (docker logs pos_app)
2. Revisar la consola del navegador (F12)
3. Contactar al equipo de desarrollo

## 📄 Licencia

Este proyecto es privado y de uso exclusivo.

## ✅ Checklist de Producción

Antes de ir a producción:

- [ ] Cambiar credenciales por defecto
- [ ] Configurar SECRET_KEY y JWT_SECRET_KEY seguros
- [ ] Verificar DEBUG=False
- [ ] Configurar backup de base de datos
- [ ] Implementar HTTPS
- [ ] Configurar dominios personalizados
- [ ] Pruebas de carga
- [ ] Documentación de procesos
- [ ] Plan de disaster recovery
- [ ] Monitoreo y alertas

---

**Versión**: 1.0.0  
**Última actualización**: Mayo 2026
