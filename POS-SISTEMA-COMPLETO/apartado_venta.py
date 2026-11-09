"""Conversión de un apartado liquidado en una venta, sin mover inventario."""
from decimal import Decimal
from models import db, Venta, DetalleVenta, PagoVenta
from business_validation import money
from config import get_cdmx_now


def registrar_venta_entrega(apartado, usuario_id):
    totales = {metodo: Decimal('0') for metodo in ('efectivo', 'tarjeta', 'transferencia')}
    for movimiento in apartado.movimientos:
        if movimiento.get('tipo') not in ('creacion', 'abonar'):
            continue
        for pago in movimiento.get('pagos', []):
            if pago.get('metodo') not in totales:
                raise ValueError('El historial contiene un método de pago inválido')
            totales[pago['metodo']] += money(pago.get('monto'))
    if sum(totales.values()) != apartado.total or apartado.abonado != apartado.total:
        raise ValueError('Los pagos del apartado no coinciden con el total liquidado')
    metodos = [metodo for metodo, monto in totales.items() if monto > 0]
    venta = Venta(numero_venta='AP-' + apartado.id, sucursal_id=apartado.sucursal_id,
                  cajero_id=usuario_id, total=apartado.total, total_impuestos=0,
                  forma_pago='mixto' if len(metodos) > 1 else (metodos[0] if metodos else 'efectivo'),
                  observaciones='Entrega de apartado AP-' + apartado.id[:8].upper(), created_at=get_cdmx_now())
    for producto in apartado.productos:
        precio = money(producto['precio'], 'Precio del apartado')
        venta.detalles.append(DetalleVenta(producto_id=producto['producto_id'], cantidad=producto['cantidad'],
                                          precio_unitario=precio, subtotal=precio*producto['cantidad'],
                                          impuesto_unitario=0, sin_stock=producto.get('faltantes', 0) > 0))
    if sum(d.subtotal for d in venta.detalles) != apartado.total:
        raise ValueError('Los productos del apartado no coinciden con el total')
    db.session.add(venta)
    db.session.flush()
    for metodo in metodos:
        db.session.add(PagoVenta(venta_id=venta.id, metodo_pago=metodo, monto=totales[metodo]))
    db.session.flush()
    return venta
