# Flujo de Devoluciones - Documentación Técnica

## 1️⃣ Obtener Ventas del Día

### Petición Frontend
```javascript
GET /api/devoluciones/ventas-dia?sucursal_id=abc123

Headers:
  Authorization: Bearer {jwt_token}

Response:
{
  "ventas": [
    {
      "id": "venta-001",
      "numero_venta": "#V001",
      "sucursal_nombre": "Centro",
      "cajero_nombre": "Juan",
      "total": 1500.50,
      "created_at": "2024-01-15T10:30:00",
      "detalles": [
        {
          "id": "detalle-001",
          "producto_nombre": "Protector de Pantalla",
          "cantidad": 2,
          "precio_unitario": 500.00,
          "subtotal": 1000.00
        }
      ]
    }
  ]
}
```

### Lógica Backend
```python
def obtener_ventas_del_dia():
  hoy = datetime.utcnow().date()
  query = Venta.query.filter(DATE(Venta.created_at) == hoy)
  
  if sucursal_id:
    query = query.filter_by(sucursal_id=sucursal_id)
  
  ventas = query.order_by(Venta.created_at.desc()).all()
  
  return {
    'ventas': [v.to_dict(include_detalles=True) for v in ventas]
  }
```

---

## 2️⃣ Registrar Devolución

### Petición Frontend
```javascript
POST /api/devoluciones

Body:
{
  "venta_id": "venta-001",
  "detalle_venta_id": "detalle-001",
  "cantidad_devuelta": 1,
  "motivo": "Defectuoso"
}

Headers:
  Authorization: Bearer {jwt_token}
  Content-Type: application/json

Response (201):
{
  "message": "Devolución registrada exitosamente",
  "devolucion": {
    "id": "dev-001",
    "numero_venta": "#V001",
    "producto_nombre": "Protector de Pantalla",
    "cantidad_devuelta": 1,
    "precio_unitario": 500.00,
    "monto_devuelto": 500.00,
    "motivo": "Defectuoso",
    "usuario_nombre": "Admin",
    "created_at": "2024-01-15T11:00:00"
  },
  "nuevo_total_venta": 1000.50
}
```

### Lógica Backend

#### Step 1: Validaciones
```python
# Validar cantidad positiva
if cantidad_devuelta <= 0:
  return {'error': 'La cantidad a devolver debe ser mayor a 0'}, 400

# Verificar venta existe
venta = Venta.query.get(venta_id)
if not venta:
  return {'error': 'Venta no encontrada'}, 404

# Verificar detalle existe y pertenece a venta
detalle = DetalleVenta.query.get(detalle_venta_id)
if not detalle or detalle.venta_id != venta_id:
  return {'error': 'Detalle de venta no encontrado'}, 404

# Validar no devolver más de lo vendido
total_devuelto = sum(d.cantidad_devuelta for d in 
                     DevolucionVenta.query
                     .filter_by(detalle_venta_id=detalle_venta_id)
                     .all())

if total_devuelto + cantidad_devuelta > detalle.cantidad:
  return {'error': f'No se puede devolver {cantidad_devuelta}. '
                   f'Total disponible: {detalle.cantidad - total_devuelto}'}, 400
```

#### Step 2: Crear Registro de Devolución
```python
devolucion = DevolucionVenta(
  venta_id=venta_id,
  detalle_venta_id=detalle_venta_id,
  cantidad_devuelta=cantidad_devuelta,
  motivo=motivo,
  usuario_id=user_id  # Admin autenticado
)
db.session.add(devolucion)
db.session.flush()
```

#### Step 3: Restaurar Stock
```python
stock = Stock.query.filter_by(
  producto_id=detalle.producto_id,
  sucursal_id=venta.sucursal_id
).first()

if stock:
  stock.cantidad += cantidad_devuelta
  # Antes: stock.cantidad = 5
  # Después: stock.cantidad = 6
```

#### Step 4: Recalcular Totales de Venta
```python
# Calcular monto devuelto (respeta decimales)
monto_devuelto = Decimal(str(detalle.precio_unitario)) * \
                 Decimal(str(cantidad_devuelta))
# Ej: 500.00 * 1 = 500.00

impuesto_devuelto = Decimal(str(detalle.impuesto_unitario)) * \
                    Decimal(str(cantidad_devuelta))
# Ej: 50.00 * 1 = 50.00

# Restar de totales de venta
venta.total -= monto_devuelto
# Antes: venta.total = 1500.50
# Después: venta.total = 1000.50

venta.total_impuestos -= impuesto_devuelto
# Antes: venta.total_impuestos = 150.00
# Después: venta.total_impuestos = 100.00

db.session.commit()
```

---

## 3️⃣ Obtener Historial de Devoluciones

### Petición Frontend
```javascript
GET /api/devoluciones?sucursal_id=abc123&fecha_inicio=2024-01-15&fecha_fin=2024-01-15

Headers:
  Authorization: Bearer {jwt_token}

Response:
{
  "devoluciones": [
    {
      "id": "dev-001",
      "numero_venta": "#V001",
      "producto_nombre": "Protector de Pantalla",
      "cantidad_devuelta": 1,
      "precio_unitario": 500.00,
      "monto_devuelto": 500.00,
      "motivo": "Defectuoso",
      "usuario_nombre": "Admin",
      "created_at": "2024-01-15T11:00:00"
    }
  ]
}
```

### Lógica Backend
```python
def listar_devoluciones():
  query = DevolucionVenta.query.join(Venta)
  
  # Filtros opcionales
  if sucursal_id:
    query = query.filter(Venta.sucursal_id == sucursal_id)
  
  if fecha_inicio:
    query = query.filter(
      DATE(DevolucionVenta.created_at) >= fecha_inicio
    )
  
  if fecha_fin:
    query = query.filter(
      DATE(DevolucionVenta.created_at) <= fecha_fin
    )
  
  devoluciones = query.order_by(
    DevolucionVenta.created_at.desc()
  ).all()
  
  return {'devoluciones': [d.to_dict() for d in devoluciones]}
```

---

## 4️⃣ Revertir Devolución (DELETE)

### Petición Frontend
```javascript
DELETE /api/devoluciones/dev-001

Headers:
  Authorization: Bearer {jwt_token}

Response (200):
{
  "message": "Devolución cancelada exitosamente",
  "nuevo_total_venta": 1500.50
}
```

### Lógica Backend

#### Step 1: Obtener Devolución
```python
devolucion = DevolucionVenta.query.get(devolucion_id)
if not devolucion:
  return {'error': 'Devolución no encontrada'}, 404

venta = devolucion.venta
detalle = devolucion.detalle_venta
```

#### Step 2: Reversar Stock
```python
stock = Stock.query.filter_by(
  producto_id=detalle.producto_id,
  sucursal_id=venta.sucursal_id
).first()

if stock:
  stock.cantidad -= devolucion.cantidad_devuelta
  # Antes: stock.cantidad = 6
  # Después: stock.cantidad = 5
```

#### Step 3: Restaurar Totales de Venta
```python
# Calcular montos a sumar de vuelta
monto_devuelto = Decimal(str(detalle.precio_unitario)) * \
                 Decimal(str(devolucion.cantidad_devuelta))

impuesto_devuelto = Decimal(str(detalle.impuesto_unitario)) * \
                    Decimal(str(devolucion.cantidad_devuelta))

# Sumar de vuelta a la venta
venta.total += monto_devuelto
# Antes: venta.total = 1000.50
# Después: venta.total = 1500.50

venta.total_impuestos += impuesto_devuelto

# Eliminar registro de devolución
db.session.delete(devolucion)
db.session.commit()
```

---

## 🔍 Estados de Datos

### Estado Inicial
```
Venta #V001:
├─ Total: $1500.50
├─ Impuestos: $150.00
└─ Detalles:
   └─ Protector (x2) @ $500.00 = $1000.00

Stock (Centro):
└─ Protectores: 5 unidades
```

### Después de Devolver 1 Protector
```
Venta #V001:
├─ Total: $1000.50  ✓ (reducido por $500)
├─ Impuestos: $100.00  ✓ (reducido por $50)
└─ Detalles:
   └─ Protector (x2) @ $500.00 = $1000.00
   
Stock (Centro):
└─ Protectores: 6 unidades  ✓ (incrementado)

Devolucion registrada:
├─ Producto: Protector
├─ Cantidad: 1
├─ Motivo: Defectuoso
└─ Fecha: 2024-01-15 11:00:00
```

### Después de Revertir Devolución
```
Venta #V001:
├─ Total: $1500.50  ✓ (restaurado)
├─ Impuestos: $150.00  ✓ (restaurado)
└─ Detalles:
   └─ Protector (x2) @ $500.00 = $1000.00

Stock (Centro):
└─ Protectores: 5 unidades  ✓ (restaurado)

Historial de Devoluciones: (vacío)
```

---

## 🛡️ Validaciones y Errores

### Error: Cantidad Mayor a Original
```
Input: cantidad_devuelta = 3
Detalle Original: cantidad = 2

Response (400):
{
  "error": "No se puede devolver 3 unidades. Total disponible: 2"
}
```

### Error: Venta No Existe
```
Input: venta_id = "venta-inexistente"

Response (404):
{
  "error": "Venta no encontrada"
}
```

### Error: Acceso Denegado (No Admin)
```
User Role: "employee"
Endpoint: POST /api/devoluciones

Response (403):
{
  "error": "Acceso denegado"
}
```

---

## 📊 Relaciones de Datos

```
User (admin)
  ├─ id: "user-123"
  ├─ username: "admin"
  └─ role: "admin"

Venta
  ├─ id: "venta-001"
  ├─ numero_venta: "#V001"
  ├─ sucursal_id: "suc-001"
  ├─ cajero_id: "user-456"
  ├─ total: 1500.50
  ├─ total_impuestos: 150.00
  └─ Detalles: [...]

DetalleVenta
  ├─ id: "detalle-001"
  ├─ venta_id: "venta-001" ←─┐
  ├─ producto_id: "prod-001"
  ├─ cantidad: 2
  ├─ precio_unitario: 500.00
  ├─ impuesto_unitario: 50.00
  └─ subtotal: 1000.00

DevolucionVenta
  ├─ id: "dev-001"
  ├─ venta_id: "venta-001" ────→ Venta
  ├─ detalle_venta_id: "detalle-001" ─→ DetalleVenta
  ├─ cantidad_devuelta: 1
  ├─ motivo: "Defectuoso"
  ├─ usuario_id: "user-123" ────→ User
  └─ created_at: "2024-01-15T11:00:00"

Stock
  ├─ id: "stock-001"
  ├─ producto_id: "prod-001"
  ├─ sucursal_id: "suc-001"
  ├─ cantidad: 5 (después de devolución: 6)
  └─ cantidad_minima: 5
```

---

## ✅ Checklist de Funcionalidad

- [x] Modelo DevolucionVenta creado con todas las columnas
- [x] Endpoint GET /api/devoluciones/ventas-dia implementado
- [x] Endpoint POST /api/devoluciones implementado con validaciones
- [x] Lógica de restauración de stock automática
- [x] Recálculo de totales de venta en devolución
- [x] Endpoint GET /api/devoluciones implementado con filtros
- [x] Endpoint DELETE /api/devoluciones/{id} implementado
- [x] Componente Vue DevolucionesView creado
- [x] Modal para registración de devolución
- [x] Historial de devoluciones visible
- [x] Capacidad de revertir devoluciones
- [x] Navegación en navbar agregada
- [x] Seguridad (@admin_required) implementada
- [x] Migración Alembic creada
