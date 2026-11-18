"""Disponibilidad de comisiones; nunca cambia ventas, pagos o inventario."""
from datetime import date, datetime, timedelta
from models import db, Comision, DevolucionVenta
from clasificacion_productos import normalizar
from config import CDMX_TZ
from business_validation import money

INICIO = date(2026, 11, 18)


def fecha_cdmx(valor):
    return CDMX_TZ.localize(valor) if valor.tzinfo is None else valor.astimezone(CDMX_TZ)


def rango(dia):
    return (CDMX_TZ.localize(datetime.combine(dia, datetime.min.time())),
            CDMX_TZ.localize(datetime.combine(dia + timedelta(days=1), datetime.min.time())))


def tipo_dispositivo(producto):
    sub = producto.subcategoria
    if not sub:
        return None
    tipos = {'celular': 'Celular', 'celulares': 'Celular', 'telefono': 'Celular',
             'telefonos': 'Celular', 'smartphone': 'Celular', 'smartphones': 'Celular',
             'tablet': 'Tablet', 'tablets': 'Tablet', 'tableta': 'Tablet', 'tabletas': 'Tablet'}
    cat = normalizar(sub.categoria.nombre)
    if cat in tipos:
        return tipos[cat]
    if cat in ('general', 'equipos', 'electronica', 'dispositivos', 'telefonia'):
        return tipos.get(normalizar(sub.nombre))
    return None


def unidades_disponibles(detalle):
    devueltas = db.session.query(db.func.sum(DevolucionVenta.cantidad_devuelta)).filter_by(
        detalle_venta_id=detalle.id).scalar() or 0
    ocupadas = {c.unidad for c in Comision.query.filter_by(detalle_venta_id=detalle.id).all()}
    pendientes = max(0, detalle.cantidad - devueltas - len(ocupadas))
    return [u for u in range(1, detalle.cantidad + 1) if u not in ocupadas][:pendientes]


def datos_unidad(detalle, unidad):
    venta = detalle.venta
    return dict(detalle_venta_id=detalle.id, unidad=unidad, venta_id=venta.id,
                numero_venta=venta.numero_venta, producto_nombre=detalle.producto.nombre,
                dispositivo=tipo_dispositivo(detalle.producto),
                costo=float(money(detalle.precio_unitario)),
                metodo_pago=venta.forma_pago, fecha_venta=fecha_cdmx(venta.created_at).isoformat(),
                sucursal_id=venta.sucursal_id, sucursal_nombre=venta.sucursal.nombre)
