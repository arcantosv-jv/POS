# 📊 SCHEMA DE BASE DE DATOS - POS Sistema

## Diagrama ER

```
┌──────────────┐
│    User      │
│──────────────│
│ id (UUID)    │◄─┐
│ username     │  │
│ password     │  │
│ role         │  │ (One-to-Many)
│ email        │  │
│ is_active    │  │
│ created_at   │  │
└──────────────┘  │
                  │
┌──────────────┐  │
│  Sucursal    │  │
│──────────────│  │
│ id (UUID)    │◄─┤
│ nombre       │  │
│ ciudad       │  │
│ direccion    │  │
│ activa       │  │
└──────────────┘  │
                  │
┌──────────────┐  │
│   Stock      │  │
│──────────────│  │
│ id (UUID)    │◄─┘
│ producto_id  ├──┐
│ sucursal_id  │  │
│ cantidad     │  │
│ cantidad_min │  │
│ created_at   │  │
│ updated_at   │  │
└──────────────┘  │
                  │
┌──────────────────┐
│   Categoria      │
│──────────────────│
│ id (UUID)        │
│ nombre           │
│ descripcion      │
│ activa           │
└──────────────────┘
         ▲
         │ One-to-Many
         │
┌──────────────────────┐
│  Subcategoria        │
│──────────────────────│
│ id (UUID)            │
│ categoria_id (FK)    │
│ nombre               │
│ descripcion          │
│ activa               │
└──────────────────────┘
         ▲
         │ One-to-Many
         │
┌──────────────────────┐
│    Producto          │
│──────────────────────│
│ id (UUID)            │
│ codigo               │
│ nombre               │
│ descripcion          │
│ precio (NULLABLE)    │
│ impuesto             │
│ subcategoria_id (FK) │
│ is_active            │
│ created_at           │
└──────────────────────┘
         ▲
         │ One-to-Many (para detalles de venta)
         │
┌──────────────────────┐      ┌─────────────────┐
│      Venta           │◄─────┤  DetalleVenta   │
│──────────────────────│      │─────────────────│
│ id (UUID)            │      │ id (UUID)       │
│ usuario_id (FK)      │      │ venta_id (FK)   │
│ sucursal_id (FK)     │      │ producto_id (FK)│
│ total                │      │ cantidad        │
│ estado               │      │ precio_unitario │
│ metodo_pago          │      │ subtotal        │
│ created_at           │      │ impuesto        │
│ updated_at           │      └─────────────────┘
└──────────────────────┘
         ▲
         │ One-to-Many
         │
┌──────────────────────────┐
│  DevolucionVenta         │
│──────────────────────────│
│ id (UUID)                │
│ venta_id (FK)            │
│ detalle_venta_id (FK)    │
│ cantidad_devuelta        │
│ motivo                   │
│ usuario_id (FK)          │
│ created_at               │
└──────────────────────────┘

Otros:
- EntradaInventario: Registro de movimientos
- Pago: Detalles de pagos por venta
- CierreCaja: Cierre diario de caja
```

---

## 📋 Tablas Detalladas

### 1. **users**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(80) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(120) UNIQUE,
    role VARCHAR(20) NOT NULL DEFAULT 'employee',  -- admin, employee
    sucursal_id UUID REFERENCES sucursal(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
```

### 2. **sucursal**
```sql
CREATE TABLE sucursal (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre VARCHAR(100) NOT NULL,
    ciudad VARCHAR(100),
    direccion VARCHAR(255),
    activa BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sucursal_nombre ON sucursal(nombre);
```

### 3. **categoria**
```sql
CREATE TABLE categoria (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT,
    activa BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_categoria_nombre ON categoria(nombre);
```

### 4. **subcategoria**
```sql
CREATE TABLE subcategoria (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    categoria_id UUID NOT NULL REFERENCES categoria(id),
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    activa BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(categoria_id, nombre)
);

CREATE INDEX idx_subcategoria_categoria_id ON subcategoria(categoria_id);
CREATE INDEX idx_subcategoria_nombre ON subcategoria(nombre);
```

### 5. **producto**
```sql
CREATE TABLE producto (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    precio NUMERIC(10,2),  -- NULLABLE para productos sin precio
    impuesto NUMERIC(5,2) DEFAULT 0,
    codigo_barras VARCHAR(100),
    subcategoria_id UUID REFERENCES subcategoria(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_producto_codigo ON producto(codigo);
CREATE INDEX idx_producto_nombre ON producto(nombre);
CREATE INDEX idx_producto_subcategoria_id ON producto(subcategoria_id);
```

### 6. **stock**
```sql
CREATE TABLE stock (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    producto_id UUID NOT NULL REFERENCES producto(id),
    sucursal_id UUID NOT NULL REFERENCES sucursal(id),
    cantidad INTEGER DEFAULT 0,
    cantidad_minima INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(producto_id, sucursal_id)
);

CREATE INDEX idx_stock_producto_id ON stock(producto_id);
CREATE INDEX idx_stock_sucursal_id ON stock(sucursal_id);
CREATE INDEX idx_stock_cantidad_minima ON stock(cantidad) WHERE cantidad <= cantidad_minima;
```

### 7. **venta**
```sql
CREATE TABLE venta (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID NOT NULL REFERENCES users(id),
    sucursal_id UUID NOT NULL REFERENCES sucursal(id),
    total NUMERIC(10,2) NOT NULL DEFAULT 0,
    estado VARCHAR(20) DEFAULT 'completada',  -- completada, devolvida
    metodo_pago VARCHAR(50),
    notas TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_venta_usuario_id ON venta(usuario_id);
CREATE INDEX idx_venta_sucursal_id ON venta(sucursal_id);
CREATE INDEX idx_venta_estado ON venta(estado);
CREATE INDEX idx_venta_fecha ON venta(created_at DESC);
```

### 8. **detalle_venta**
```sql
CREATE TABLE detalle_venta (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venta_id UUID NOT NULL REFERENCES venta(id),
    producto_id UUID NOT NULL REFERENCES producto(id),
    cantidad INTEGER NOT NULL,
    precio_unitario NUMERIC(10,2) NOT NULL,
    subtotal NUMERIC(10,2),
    impuesto NUMERIC(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_detalle_venta_venta_id ON detalle_venta(venta_id);
CREATE INDEX idx_detalle_venta_producto_id ON detalle_venta(producto_id);
```

### 9. **devolucion_venta**
```sql
CREATE TABLE devolucion_venta (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venta_id UUID NOT NULL REFERENCES venta(id),
    detalle_venta_id UUID NOT NULL REFERENCES detalle_venta(id),
    cantidad_devuelta INTEGER NOT NULL,
    motivo VARCHAR(255),
    usuario_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_devolucion_venta_venta_id ON devolucion_venta(venta_id);
CREATE INDEX idx_devolucion_venta_usuario_id ON devolucion_venta(usuario_id);
```

### 10. **entrada_inventario**
```sql
CREATE TABLE entrada_inventario (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id UUID NOT NULL REFERENCES stock(id),
    cantidad INTEGER NOT NULL,
    concepto VARCHAR(100),
    usuario_id UUID REFERENCES users(id),
    notas TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_entrada_inventario_stock_id ON entrada_inventario(stock_id);
CREATE INDEX idx_entrada_inventario_usuario_id ON entrada_inventario(usuario_id);
```

### 11. **pago**
```sql
CREATE TABLE pago (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venta_id UUID NOT NULL REFERENCES venta(id),
    metodo VARCHAR(50) NOT NULL,  -- efectivo, tarjeta, cheque
    monto NUMERIC(10,2) NOT NULL,
    referencia VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pago_venta_id ON pago(venta_id);
CREATE INDEX idx_pago_metodo ON pago(metodo);
```

### 12. **cierre_caja**
```sql
CREATE TABLE cierre_caja (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID NOT NULL REFERENCES users(id),
    sucursal_id UUID NOT NULL REFERENCES sucursal(id),
    efectivo_reportado NUMERIC(10,2) NOT NULL,
    observaciones TEXT,
    estado VARCHAR(20) DEFAULT 'cerrado',  -- cerrado, corregido
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cierre_caja_usuario_id ON cierre_caja(usuario_id);
CREATE INDEX idx_cierre_caja_sucursal_id ON cierre_caja(sucursal_id);
CREATE INDEX idx_cierre_caja_fecha ON cierre_caja(created_at DESC);
```

---

## 🔑 Estrategia de Claves

- **Primary Key**: UUID v4 para distribuibilidad
- **Foreign Keys**: Con cascada para integridad referencial
- **Índices**: En campos de búsqueda frecuente y FK
- **Unique**: Donde se requiera unicidad (código producto, username, etc)

---

## 🔄 Migraciones

Las migraciones se encuentran en `migrations/versions/`:

1. **001_initial_migration.py** - Tablas base
2. **002_add_pagos_venta.py** - Tabla de pagos
3. **003_add_cierres_caja.py** - Tabla de cierre de caja
4. **004_make_precio_nullable.py** - Hacer nullable precio
5. **005_create_devoluciones_venta.py** - Tabla de devoluciones

Ejecutar migraciones:
```bash
flask db upgrade  # Ejecutar todas
flask db current  # Ver versión actual
flask db history  # Ver historial
```

---

## 📈 Optimización

### Índices Recomendados
```sql
-- Performance en búsquedas
CREATE INDEX idx_producto_search ON producto 
USING GIN(to_tsvector('spanish', nombre || ' ' || COALESCE(descripcion, '')));

-- Performance en reportes
CREATE INDEX idx_venta_fecha_usuario ON venta(created_at DESC, usuario_id);

-- Performance en stock bajo
CREATE INDEX idx_stock_bajo ON stock 
WHERE cantidad <= cantidad_minima;
```

### Estadísticas
```sql
-- Actualizar estadísticas regularmente
ANALYZE users;
ANALYZE venta;
ANALYZE stock;
```

---

## 🔒 Seguridad

- **Passwords**: Hasheados con bcrypt (never stored in plain text)
- **UUIDs**: Como PKs en lugar de IDs secuenciales
- **Foreign Keys**: Previenen orfanatos de datos
- **Auditoría**: Todos los registros tienen `created_at` y `updated_at`
- **ACID**: Transacciones garantizadas por PostgreSQL

---

## 💾 Backups

```bash
# Crear backup
pg_dump pos_db > backup.sql

# Restaurar backup
psql pos_db < backup.sql

# Backup comprimido
pg_dump pos_db | gzip > backup_$(date +%Y%m%d).sql.gz
```

---

## ✅ Verificación de Integridad

```sql
-- Verificar referencias huérfanas
SELECT * FROM venta WHERE usuario_id NOT IN (SELECT id FROM users);
SELECT * FROM stock WHERE producto_id NOT IN (SELECT id FROM producto);

-- Verificar stocks negativos
SELECT * FROM stock WHERE cantidad < 0;

-- Listar tablas
\dt+

-- Ver definición de tabla
\d+ venta
```
