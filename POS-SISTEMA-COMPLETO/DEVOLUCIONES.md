# Implementación de Sistema de Devoluciones (Devoluciónessistema POS

## 📋 Resumen

Se ha implementado un sistema completo de gestión de devoluciones de productos que permite a los administradores:

- Ver todas las ventas del día filtradas por sucursal
- Seleccionar un producto vendido y registrar su devolución
- Automatizar la restauración de inventario
- Calcular automáticamente el nuevo total de la venta
- Mantener un historial de devoluciones
- Revertir devoluciones si es necesario

## 🔧 Cambios Realizados

### 1. Backend - Modelos (models.py)

**Nuevo Modelo: DevolucionVenta**
- Tabla: `devoluciones_venta`
- Campos:
  - `id` - UUID primario
  - `venta_id` - FK a Venta
  - `detalle_venta_id` - FK a DetalleVenta
  - `cantidad_devuelta` - Cantidad del producto devuelto
  - `motivo` - Razón de la devolución
  - `usuario_id` - Admin que registró la devolución
  - `created_at` - Timestamp

```python
class DevolucionVenta(db.Model):
    __tablename__ = 'devoluciones_venta'
    # ... (ver models.py lineas 338-366)
```

### 2. Backend - API (routes_devoluciones.py)

**4 Endpoints principales:**

```
GET  /api/devoluciones/ventas-dia?sucursal_id=X
POST /api/devoluciones
GET  /api/devoluciones?sucursal_id=X&fecha_inicio=Y&fecha_fin=Z
DELETE /api/devoluciones/{id}
```

**Lógica de negocio:**

- **GET ventas-dia**: Retorna todas las ventas del día con sus detalles incluidos
- **POST devolucion**: 
  - Valida cantidad devuelta no exceda original
  - Restaura stock automáticamente
  - Recalcula total de venta
  - Crea registro de devolución
- **GET devoluciones**: Lista historial con filtros
- **DELETE devolucion**: Revierte devolución restaurando total original

### 3. Frontend - Componente Vue (components.js)

**DevolucionesView Component** (lineas ~3548-3900+)

**Data:**
- Sucursales, ventas, devoluciones, venta seleccionada
- Modal para capturar devolución
- Cantidad y motivo de devolución

**Features:**
- Selector de sucursal con filtrado en tiempo real
- Tabla expandible de ventas del día
- Vista detallada de productos por venta
- Modal para registrar devolución con:
  - Selector de cantidad devuelta
  - Dropdown de motivos predefinidos
  - Campo de notas adicionales
  - Cálculo automático de monto a revertir
- Historial de devoluciones registradas
- Botón para revertir devoluciones

### 4. Integración Frontend (index.html & app.js)

**Cambios:**
- Agregado link "Devoluciones" en navbar (solo para admin)
- Registrado componente 'devoluciones-view' en app.js
- Agregado punto de montaje para el componente

### 5. Base de Datos (Alembic Migration)

**Archivo:** `migrations/versions/005_create_devoluciones_venta.py`
- Crea tabla devoluciones_venta con estructura adecuada
- Índices en venta_id y usuario_id para performance
- Foreign keys correctamente referenciadas

## 🚀 Cómo Usar

### Para Administrador:

1. **Ir a módulo Devoluciones**
   - Navegar desde el menú superior → "Devoluciones"

2. **Seleccionar Sucursal** (opcional)
   - Elegir sucursal para filtrar ventas
   - Click en "Cargar Ventas"

3. **Ver Ventas del Día**
   - Se muestran todas las ventas de la sucursal
   - Mostrando número, hora, cajero y total

4. **Expandir Venta**
   - Click sobre una venta para ver detalles
   - Se despliegan todos los productos con cantidades

5. **Registrar Devolución**
   - Click en botón "Devolver" del producto
   - Modal solicita:
     - Cantidad a devolver (validado vs cantidad original)
     - Motivo (predefinidos: Defectuoso, Cambio opinión, etc.)
     - Notas adicionales (opcional)
   - Click "Registrar Devolución"

6. **Confirmación Automática**
   - Stock se restaura automáticamente
   - Total de venta se recalcula
   - Historial se actualiza

7. **Ver Historial**
   - Sección inferior muestra todas las devoluciones
   - Incluye: venta, producto, cantidad, monto, motivo, admin, fecha
   - Opción "Revertir" para deshacer devoluciones

## 💾 Base de Datos

Estructura de la tabla `devoluciones_venta`:

```sql
CREATE TABLE devoluciones_venta (
    id VARCHAR(36) PRIMARY KEY,
    venta_id VARCHAR(36) NOT NULL REFERENCES ventas(id),
    detalle_venta_id VARCHAR(36) NOT NULL REFERENCES detalles_venta(id),
    cantidad_devuelta INTEGER NOT NULL,
    motivo TEXT,
    usuario_id VARCHAR(36) NOT NULL REFERENCES users(id),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    INDEX ix_devoluciones_venta_venta_id (venta_id),
    INDEX ix_devoluciones_venta_usuario_id (usuario_id)
);
```

## 🔒 Seguridad

- ✅ **Autenticación**: Requiere JWT token válido
- ✅ **Autorización**: Solo admin puede acceder (@admin_required)
- ✅ **Validaciones**:
  - Cantidad devuelta no puede exceder cantidad original
  - No permite cantidades negativas o cero
  - Verifica que venta y detalle existan

## 📊 Flujo de Transacciones

```
Usuario Admin
     ↓
[GET /api/devoluciones/ventas-dia] → Obtiene ventas del día
     ↓
[Selecciona venta y producto]
     ↓
[POST /api/devoluciones] → Registra devolución
     ↓
  ├─ Valida cantidad
  ├─ Stock.cantidad += cantidad_devuelta
  ├─ Venta.total -= monto_devuelto
  ├─ Venta.total_impuestos -= impuesto_devuelto
  └─ Crea DevolucionVenta record
     ↓
[GET /api/devoluciones] → Obtiene historial actualizado
```

## 🧪 Testing

Para probar manualmente:

1. **Crear una venta** en módulo de Ventas
2. **Navegar a Devoluciones**
3. **Registrar una devolución**
4. **Verificar:**
   - Stock incrementado ✓
   - Total de venta recalculado ✓
   - Historial actualizado ✓
5. **Revertir devolución** y verificar todo vuelva a estado original ✓

## 📝 Notas Técnicas

- Todas las operaciones de dinero usan `Decimal` para precisión
- Los filtros de devoluciones son con parámetros GET para caching
- El componente reutiliza métodos de formatting (formatoMoneda, formatoFecha)
- La modal se abre/cierra mediante v-if sobre variable de data booleana

## 🔄 Próximas Mejoras (Opcionales)

- [ ] Exportar historial de devoluciones a Excel/PDF
- [ ] Notificación por email al registrar devolución
- [ ] Reporte de devoluciones por motivo
- [ ] Límite temporal para realizar devoluciones
- [ ] Foto de producto devuelto
- [ ] QR para seguimiento de devoluciones
