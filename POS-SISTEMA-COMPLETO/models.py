from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func
import bcrypt
import uuid
import random
from config import get_cdmx_now

db = SQLAlchemy()

def generate_venta_id():
    """Genera un ID de venta alfanumérico de 10 caracteres (ej: A3K9X2M7B1)"""
    import string
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(10))

class User(db.Model):
    """Modelo de usuario"""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')  # admin, employee
    sucursal_id = db.Column(db.String(36), db.ForeignKey('sucursales.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_cdmx_now)
    updated_at = db.Column(db.DateTime, default=get_cdmx_now, onupdate=get_cdmx_now)
    
    # Relationships
    sucursal = db.relationship('Sucursal', backref='users')
    ventas = db.relationship('Venta', backref='cajero')
    
    def set_password(self, password):
        """Hashear contraseña"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        """Verificar contraseña"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'sucursal_id': self.sucursal_id,
            'sucursal_nombre': self.sucursal.nombre if self.sucursal else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }

class Sucursal(db.Model):
    """Modelo de sucursal"""
    __tablename__ = 'sucursales'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = db.Column(db.String(120), nullable=False, unique=True)
    direccion = db.Column(db.String(255), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)
    ciudad = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_cdmx_now)
    
    # Relationships
    stocks = db.relationship('Stock', backref='sucursal', cascade='all, delete-orphan')
    ventas = db.relationship('Venta', backref='sucursal')
    entradas_inventario = db.relationship('EntradaInventario', backref='sucursal')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'direccion': self.direccion,
            'telefono': self.telefono,
            'ciudad': self.ciudad,
            'is_active': self.is_active
        }

class Categoria(db.Model):
    """Modelo de categoría de productos"""
    __tablename__ = 'categorias'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_cdmx_now)
    
    # Relationships
    subcategorias = db.relationship('Subcategoria', backref='categoria', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'is_active': self.is_active
        }

class Subcategoria(db.Model):
    """Modelo de subcategoría de productos"""
    __tablename__ = 'subcategorias'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    categoria_id = db.Column(db.String(36), db.ForeignKey('categorias.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_cdmx_now)
    
    # Relationships
    productos = db.relationship('Producto', backref='subcategoria', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.UniqueConstraint('nombre', 'categoria_id', name='uq_subcategoria_nombre_categoria'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'categoria_id': self.categoria_id,
            'is_active': self.is_active
        }

class Producto(db.Model):
    """Modelo de producto"""
    __tablename__ = 'productos'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    codigo = db.Column(db.String(50), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    precio = db.Column(db.Numeric(10, 2), nullable=True)
    impuesto = db.Column(db.Numeric(5, 2), default=0)  # Porcentaje de impuesto
    subcategoria_id = db.Column(db.String(36), db.ForeignKey('subcategorias.id'), nullable=False)
    codigo_barras = db.Column(db.String(100), nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_cdmx_now)
    updated_at = db.Column(db.DateTime, default=get_cdmx_now, onupdate=get_cdmx_now)
    
    # Relationships
    stocks = db.relationship('Stock', backref='producto', cascade='all, delete-orphan')
    detalles_venta = db.relationship('DetalleVenta', backref='producto')
    entradas_inventario = db.relationship('EntradaInventario', backref='producto')
    
    def to_dict(self, include_stock=False):
        data = {
            'id': self.id,
            'codigo': self.codigo,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'precio': float(self.precio) if self.precio is not None else None,
            'impuesto': float(self.impuesto) if self.impuesto is not None else 0,
            'subcategoria_id': self.subcategoria_id,
            'categoria_id': self.subcategoria.categoria_id if self.subcategoria else None,
            'codigo_barras': self.codigo_barras,
            'is_active': self.is_active
        }
        if include_stock:
            data['stocks'] = [stock.to_dict() for stock in self.stocks]
        return data

class Stock(db.Model):
    """Modelo de stock de producto por sucursal"""
    __tablename__ = 'stocks'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    producto_id = db.Column(db.String(36), db.ForeignKey('productos.id'), nullable=False)
    sucursal_id = db.Column(db.String(36), db.ForeignKey('sucursales.id'), nullable=False)
    cantidad = db.Column(db.Integer, default=0)
    cantidad_minima = db.Column(db.Integer, default=5)
    updated_at = db.Column(db.DateTime, default=get_cdmx_now, onupdate=get_cdmx_now)
    
    __table_args__ = (
        db.UniqueConstraint('producto_id', 'sucursal_id', name='uq_stock_producto_sucursal'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'producto_id': self.producto_id,
            'sucursal_id': self.sucursal_id,
            'cantidad': self.cantidad,
            'cantidad_minima': self.cantidad_minima
        }

class EntradaInventario(db.Model):
    """Modelo para registrar entradas de inventario (compras a proveedores)"""
    __tablename__ = 'entradas_inventario'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    producto_id = db.Column(db.String(36), db.ForeignKey('productos.id'), nullable=False)
    sucursal_id = db.Column(db.String(36), db.ForeignKey('sucursales.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    numero_entrada = db.Column(db.String(50), unique=True, nullable=False)
    observaciones = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=get_cdmx_now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'producto_id': self.producto_id,
            'producto_nombre': self.producto.nombre,
            'sucursal_id': self.sucursal_id,
            'cantidad': self.cantidad,
            'numero_entrada': self.numero_entrada,
            'observaciones': self.observaciones,
            'created_at': self.created_at.isoformat()
        }

class Venta(db.Model):
    """Modelo de venta"""
    __tablename__ = 'ventas'
    
    id = db.Column(db.String(10), primary_key=True, default=generate_venta_id)
    numero_venta = db.Column(db.String(50), unique=True, nullable=False)
    sucursal_id = db.Column(db.String(36), db.ForeignKey('sucursales.id'), nullable=False)
    cajero_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    total_impuestos = db.Column(db.Numeric(10, 2), default=0)
    forma_pago = db.Column(db.String(50), nullable=False)  # efectivo, tarjeta, transferencia, etc
    observaciones = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=get_cdmx_now, index=True)
    updated_at = db.Column(db.DateTime, default=get_cdmx_now, onupdate=get_cdmx_now)
    
    # Relationships (implícitas desde User y Sucursal backref)
    detalles = db.relationship('DetalleVenta', backref='venta', cascade='all, delete-orphan')
    
    def to_dict(self, include_detalles=False):
        data = {
            'id': self.id,
            'numero_venta': self.numero_venta,
            'sucursal_id': self.sucursal_id,
            'sucursal_nombre': self.sucursal.nombre,
            'cajero_id': self.cajero_id,
            'cajero_nombre': self.cajero.username,
            'total': float(self.total),
            'total_impuestos': float(self.total_impuestos),
            'forma_pago': self.forma_pago,
            'observaciones': self.observaciones,
            'created_at': self.created_at.isoformat()
        }
        if include_detalles:
            data['detalles'] = [detalle.to_dict() for detalle in self.detalles]
        return data

class DetalleVenta(db.Model):
    """Modelo de detalle de venta (productos en una venta)"""
    __tablename__ = 'detalles_venta'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    venta_id = db.Column(db.String(36), db.ForeignKey('ventas.id'), nullable=False)
    producto_id = db.Column(db.String(36), db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    impuesto_unitario = db.Column(db.Numeric(5, 2), default=0)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    sin_stock = db.Column(db.Boolean, default=False)  # Indica si fue vendido sin stock disponible
    
    def to_dict(self):
        return {
            'id': self.id,
            'venta_id': self.venta_id,
            'producto_id': self.producto_id,
            'producto_nombre': self.producto.nombre,
            'cantidad': self.cantidad,
            'precio_unitario': float(self.precio_unitario),
            'impuesto_unitario': float(self.impuesto_unitario),
            'subtotal': float(self.subtotal),
            'sin_stock': self.sin_stock
        }

class PagoVenta(db.Model):
    """Modelo para desglose de pagos mixtos en una venta"""
    __tablename__ = 'pagos_venta'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    venta_id = db.Column(db.String(36), db.ForeignKey('ventas.id'), nullable=False)
    metodo_pago = db.Column(db.String(50), nullable=False)  # efectivo, tarjeta, transferencia, etc
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=get_cdmx_now)
    
    # Relationship
    venta = db.relationship('Venta', backref='pagos')
    
    def to_dict(self):
        return {
            'id': self.id,
            'venta_id': self.venta_id,
            'metodo_pago': self.metodo_pago,
            'monto': float(self.monto)
        }

class CierreCaja(db.Model):
    """Modelo para cierre de caja diario"""
    __tablename__ = 'cierres_caja'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empleado_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    sucursal_id = db.Column(db.String(36), db.ForeignKey('sucursales.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False, index=True)
    
    # Totales calculados
    total_ventas = db.Column(db.Numeric(10, 2), default=0)
    total_efectivo = db.Column(db.Numeric(10, 2), default=0)
    total_tarjeta = db.Column(db.Numeric(10, 2), default=0)
    total_transferencia = db.Column(db.Numeric(10, 2), default=0)
    
    # Efectivo físico reportado
    efectivo_reportado = db.Column(db.Numeric(10, 2), nullable=True)
    diferencia = db.Column(db.Numeric(10, 2), nullable=True)  # efectivo_reportado - total_efectivo
    
    # Estado
    estado = db.Column(db.String(20), default='abierto')  # abierto, cerrado
    observaciones = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=get_cdmx_now)
    updated_at = db.Column(db.DateTime, default=get_cdmx_now, onupdate=get_cdmx_now)
    
    # Relationships
    empleado = db.relationship('User', backref='cierres_caja')
    sucursal = db.relationship('Sucursal', backref='cierres_caja')
    
    def to_dict(self):
        return {
            'id': self.id,
            'empleado_id': self.empleado_id,
            'empleado_nombre': self.empleado.username,
            'sucursal_id': self.sucursal_id,
            'sucursal_nombre': self.sucursal.nombre,
            'fecha': self.fecha.isoformat(),
            'total_ventas': float(self.total_ventas),
            'total_efectivo': float(self.total_efectivo),
            'total_tarjeta': float(self.total_tarjeta),
            'total_transferencia': float(self.total_transferencia),
            'efectivo_reportado': float(self.efectivo_reportado) if self.efectivo_reportado else None,
            'diferencia': float(self.diferencia) if self.diferencia else None,
            'estado': self.estado,
            'observaciones': self.observaciones,
            'created_at': self.created_at.isoformat()
        }

class DevolucionVenta(db.Model):
    """Modelo para registrar devoluciones de productos de una venta"""
    __tablename__ = 'devoluciones_venta'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    venta_id = db.Column(db.String(36), db.ForeignKey('ventas.id'), nullable=False)
    detalle_venta_id = db.Column(db.String(36), db.ForeignKey('detalles_venta.id'), nullable=False)
    cantidad_devuelta = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.Text, nullable=True)
    usuario_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=get_cdmx_now)
    
    # Relationships
    venta = db.relationship('Venta', backref='devoluciones')
    detalle_venta = db.relationship('DetalleVenta', backref='devoluciones')
    usuario = db.relationship('User', backref='devoluciones')
    
    def to_dict(self):
        detalle = self.detalle_venta
        return {
            'id': self.id,
            'venta_id': self.venta_id,
            'numero_venta': self.venta.numero_venta,
            'producto_id': detalle.producto_id,
            'producto_nombre': detalle.producto.nombre,
            'cantidad_devuelta': self.cantidad_devuelta,
            'precio_unitario': float(detalle.precio_unitario),
            'monto_devuelto': float(detalle.precio_unitario * self.cantidad_devuelta),
            'motivo': self.motivo,
            'usuario_nombre': self.usuario.username,
            'created_at': self.created_at.isoformat()
        }

# ==================== MODELOS PARA REPARACIONES ====================

class MarcaDispositivo(db.Model):
    """Modelo para marcas de dispositivos móviles"""
    __tablename__ = 'marcas_dispositivos'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_cdmx_now)
    
    # Relationships
    modelos = db.relationship('ModeloDispositivo', backref='marca', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'is_active': self.is_active
        }

class ModeloDispositivo(db.Model):
    """Modelo para modelos específicos de dispositivos"""
    __tablename__ = 'modelos_dispositivos'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    marca_id = db.Column(db.String(36), db.ForeignKey('marcas_dispositivos.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_cdmx_now)
    
    __table_args__ = (
        db.UniqueConstraint('marca_id', 'nombre', name='uq_modelo_marca_nombre'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'marca_id': self.marca_id,
            'marca_nombre': self.marca.nombre if self.marca else None,
            'nombre': self.nombre,
            'is_active': self.is_active
        }

class TipoReparacion(db.Model):
    """Modelo para tipos de reparaciones"""
    __tablename__ = 'tipos_reparacion'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_cdmx_now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'is_active': self.is_active
        }

class CatalogoReparacion(db.Model):
    """Modelo para catálogo de reparaciones con precios"""
    __tablename__ = 'catalogo_reparaciones'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    marca_id = db.Column(db.String(36), db.ForeignKey('marcas_dispositivos.id'), nullable=False)
    modelo_id = db.Column(db.String(36), db.ForeignKey('modelos_dispositivos.id'), nullable=False)
    tipo_reparacion_id = db.Column(db.String(36), db.ForeignKey('tipos_reparacion.id'), nullable=False)
    costo = db.Column(db.Numeric(10, 2), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_cdmx_now)
    updated_at = db.Column(db.DateTime, default=get_cdmx_now, onupdate=get_cdmx_now)
    
    # Relationships
    marca = db.relationship('MarcaDispositivo')
    modelo = db.relationship('ModeloDispositivo')
    tipo_reparacion = db.relationship('TipoReparacion')
    
    __table_args__ = (
        db.UniqueConstraint('marca_id', 'modelo_id', 'tipo_reparacion_id', name='uq_catalogo_reparacion'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'marca_id': self.marca_id,
            'marca_nombre': self.marca.nombre if self.marca else None,
            'modelo_id': self.modelo_id,
            'modelo_nombre': self.modelo.nombre if self.modelo else None,
            'tipo_reparacion_id': self.tipo_reparacion_id,
            'tipo_reparacion_nombre': self.tipo_reparacion.nombre if self.tipo_reparacion else None,
            'costo': float(self.costo),
            'is_active': self.is_active
        }

class Reparacion(db.Model):
    """Modelo para registrar reparaciones de dispositivos"""
    __tablename__ = 'reparaciones'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    fecha = db.Column(db.Date, default=lambda: get_cdmx_now().date())
    nombre_cliente = db.Column(db.String(100), nullable=False)
    telefono_cliente = db.Column(db.String(20), nullable=False)
    marca_id = db.Column(db.String(36), db.ForeignKey('marcas_dispositivos.id'), nullable=False)
    modelo_id = db.Column(db.String(36), db.ForeignKey('modelos_dispositivos.id'), nullable=False)
    tipo_reparacion_id = db.Column(db.String(36), db.ForeignKey('tipos_reparacion.id'), nullable=False)
    costo = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.String(20), default='registrada')  # registrada, entregada
    sucursal_id = db.Column(db.String(36), db.ForeignKey('sucursales.id'), nullable=False)
    empleado_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    fecha_entrega = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=get_cdmx_now, index=True)
    updated_at = db.Column(db.DateTime, default=get_cdmx_now, onupdate=get_cdmx_now)
    
    # Relationships
    marca = db.relationship('MarcaDispositivo')
    modelo = db.relationship('ModeloDispositivo')
    tipo_reparacion = db.relationship('TipoReparacion')
    sucursal = db.relationship('Sucursal', backref='reparaciones')
    empleado = db.relationship('User', backref='reparaciones')
    
    def to_dict(self):
        return {
            'id': self.id,
            'fecha': self.fecha.isoformat(),
            'nombre_cliente': self.nombre_cliente,
            'telefono_cliente': self.telefono_cliente,
            'marca_id': self.marca_id,
            'marca_nombre': self.marca.nombre if self.marca else None,
            'modelo_id': self.modelo_id,
            'modelo_nombre': self.modelo.nombre if self.modelo else None,
            'tipo_reparacion_id': self.tipo_reparacion_id,
            'tipo_reparacion_nombre': self.tipo_reparacion.nombre if self.tipo_reparacion else None,
            'costo': float(self.costo),
            'estado': self.estado,
            'sucursal_id': self.sucursal_id,
            'sucursal_nombre': self.sucursal.nombre if self.sucursal else None,
            'empleado_id': self.empleado_id,
            'empleado_nombre': self.empleado.username if self.empleado else None,
            'fecha_entrega': self.fecha_entrega.isoformat() if self.fecha_entrega else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
