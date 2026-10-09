from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Venta, DetalleVenta, DevolucionVenta, Stock, Producto
from decimal import Decimal
from datetime import datetime
from config import get_cdmx_now
from cash_accounting import net_payments, set_net_payments, validate_refunds, ensure_cash_open, refresh_open_cash
from business_validation import money

devoluciones_bp = Blueprint('devoluciones', __name__, url_prefix='/api/devoluciones')

def admin_required(fn):
    """Decorador para verificar permisos de admin"""
    from functools import wraps
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Acceso denegado'}), 403
        return fn(*args, **kwargs)
    return wrapper

# ==================== DEVOLUCIONES ====================

@devoluciones_bp.route('/ventas-dia', methods=['GET'])
@admin_required
def obtener_ventas_del_dia():
    """Obtener ventas del día por sucursal para mostrar en devoluciones"""
    sucursal_id = request.args.get('sucursal_id')
    try:
        hoy = get_cdmx_now().date()
        
        query = Venta.query.filter(
            db.func.DATE(Venta.created_at) == hoy
        )
        
        if sucursal_id:
            query = query.filter_by(sucursal_id=sucursal_id)
        
        ventas = query.order_by(Venta.created_at.desc()).all()
        
        result = []
        for venta in ventas:
            item = venta.to_dict(include_detalles=True)
            try:
                item['pagos_disponibles'] = {k: float(v) for k, v in net_payments(venta).items()}
            except ValueError as error:
                item['error_conciliacion'] = str(error)
                item['pagos_disponibles'] = {}
            result.append(item)
        return jsonify({'ventas': result}), 200
    
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@devoluciones_bp.route('', methods=['POST'])
@admin_required
def crear_devolucion():
    """Crear una devolución de un producto de una venta"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validaciones
        venta_id = data.get('venta_id')
        detalle_venta_id = data.get('detalle_venta_id')
        cantidad_devuelta = int(data.get('cantidad_devuelta', 0))
        if isinstance(data.get('cantidad_devuelta'), bool) or Decimal(str(data.get('cantidad_devuelta', 0))) != cantidad_devuelta:
            raise ValueError('La cantidad a devolver debe ser un número entero')
        motivo = data.get('motivo', '')
        
        if cantidad_devuelta <= 0:
            return jsonify({'error': 'La cantidad a devolver debe ser mayor a 0'}), 400
        
        # Obtener venta y detalle
        venta = db.session.get(Venta, venta_id)
        if not venta:
            return jsonify({'error': 'Venta no encontrada'}), 404
        
        User.query.filter_by(id=venta.cajero_id).with_for_update().first()
        venta = Venta.query.filter_by(id=venta_id).populate_existing().with_for_update().one()
        detalle = DetalleVenta.query.get(detalle_venta_id)
        if not detalle or detalle.venta_id != venta_id:
            return jsonify({'error': 'Detalle de venta no encontrado'}), 404
        
        # Validar que no se devuelva más de lo que se vendió
        total_devuelto = db.session.query(db.func.sum(DevolucionVenta.cantidad_devuelta)).filter_by(
            detalle_venta_id=detalle_venta_id
        ).scalar() or 0
        
        if total_devuelto + cantidad_devuelta > detalle.cantidad:
            return jsonify({
                'error': f'No se puede devolver {cantidad_devuelta} unidades. '
                         f'Total disponible: {detalle.cantidad - total_devuelto}'
            }), 400
        
        monto_devuelto = money(detalle.precio_unitario * cantidad_devuelta)
        available = net_payments(venta)
        refunds = validate_refunds(data.get('reembolsos'), monto_devuelto, available)
        caja_empleado_id = venta.cajero_id
        ensure_cash_open(caja_empleado_id, venta.sucursal_id)

        # Crear registro de devolución
        devolucion = DevolucionVenta(
            venta_id=venta_id,
            detalle_venta_id=detalle_venta_id,
            cantidad_devuelta=cantidad_devuelta,
            motivo=motivo,
            usuario_id=user_id,
            caja_empleado_id=caja_empleado_id,
            fecha_movimiento=get_cdmx_now().date(),
            reembolsos={method: str(amount) for method, amount in refunds.items()}
        )
        
        db.session.add(devolucion)
        db.session.flush()
        
        # Actualizar stock: devolver la cantidad al inventario
        stock = Stock.query.filter_by(
            producto_id=detalle.producto_id,
            sucursal_id=venta.sucursal_id
        ).first()
        
        if not detalle.sin_stock:
            if stock:
                stock.cantidad += cantidad_devuelta
            else:
                db.session.add(Stock(producto_id=detalle.producto_id, sucursal_id=venta.sucursal_id, cantidad=cantidad_devuelta))
        
        # Actualizar total de la venta (restar el monto devuelto)
        monto_devuelto = Decimal(str(detalle.precio_unitario)) * Decimal(str(cantidad_devuelta))
        impuesto_devuelto = Decimal(str(detalle.impuesto_unitario)) * Decimal(str(cantidad_devuelta))
        
        venta.total -= monto_devuelto
        venta.total_impuestos -= impuesto_devuelto
        set_net_payments(venta, {method: amount - refunds.get(method, 0) for method, amount in available.items()})
        refresh_open_cash(caja_empleado_id, venta.sucursal_id)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Devolución registrada exitosamente',
            'devolucion': devolucion.to_dict(),
            'nuevo_total_venta': float(venta.total)
        }), 201
    
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@devoluciones_bp.route('', methods=['GET'])
@admin_required
def listar_devoluciones():
    """Listar devoluciones con filtros opcionales"""
    try:
        sucursal_id = request.args.get('sucursal_id')
        fecha_inicio = request.args.get('fecha_inicio')  # YYYY-MM-DD
        fecha_fin = request.args.get('fecha_fin')  # YYYY-MM-DD
        
        query = DevolucionVenta.query.join(Venta)
        
        if sucursal_id:
            query = query.filter(Venta.sucursal_id == sucursal_id)
        
        if fecha_inicio:
            try:
                fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                query = query.filter(db.func.DATE(DevolucionVenta.created_at) >= fecha_inicio_dt)
            except ValueError:
                return jsonify({'error': 'Formato de fecha_inicio inválido (YYYY-MM-DD)'}), 400
        
        if fecha_fin:
            try:
                fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                query = query.filter(db.func.DATE(DevolucionVenta.created_at) <= fecha_fin_dt)
            except ValueError:
                return jsonify({'error': 'Formato de fecha_fin inválido (YYYY-MM-DD)'}), 400
        
        devoluciones = query.order_by(DevolucionVenta.created_at.desc()).all()
        
        return jsonify({
            'devoluciones': [d.to_dict() for d in devoluciones]
        }), 200
    
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@devoluciones_bp.route('/<devolucion_id>', methods=['DELETE'])
@admin_required
def cancelar_devolucion(devolucion_id):
    """Cancelar una devolución (reversar el proceso)"""
    try:
        devolucion = DevolucionVenta.query.get(devolucion_id)
        if not devolucion:
            return jsonify({'error': 'Devolución no encontrada'}), 404
        
        User.query.filter_by(id=devolucion.caja_empleado_id or devolucion.venta.cajero_id).with_for_update().first()
        devolucion = DevolucionVenta.query.filter_by(id=devolucion_id).populate_existing().first()
        if not devolucion:
            return jsonify({'error': 'La devolución ya fue revertida'}), 409
        if devolucion.cierre_caja_id:
            return jsonify({'error': 'Este reembolso pertenece a un cierre confirmado y no se puede revertir'}), 409
        venta = Venta.query.filter_by(id=devolucion.venta_id).with_for_update().one()
        detalle = devolucion.detalle_venta
        if devolucion.reembolsos is None:
            return jsonify({'error': 'Devolución histórica sin método de reembolso registrado; requiere conciliación manual antes de revertir'}), 409
        refund_day = devolucion.fecha_movimiento
        if refund_day != get_cdmx_now().date():
            return jsonify({'error': 'Solo se pueden revertir reembolsos del día para no alterar cajas anteriores'}), 409
        ensure_cash_open(devolucion.caja_empleado_id, venta.sucursal_id)
        available = net_payments(venta)
        refunds = {k: Decimal(str(v)) for k, v in devolucion.reembolsos.items()}
        employee_id = devolucion.caja_empleado_id
        
        # Reversar stock: restar la cantidad devuelta
        stock = Stock.query.filter_by(
            producto_id=detalle.producto_id,
            sucursal_id=venta.sucursal_id
        ).first()
        
        if not detalle.sin_stock:
            if not stock or stock.cantidad < devolucion.cantidad_devuelta:
                return jsonify({'error': 'No hay inventario suficiente para revertir esta devolución'}), 400
            stock.cantidad -= devolucion.cantidad_devuelta
        
        # Reversar total de venta: sumar de nuevo el monto
        monto_devuelto = Decimal(str(detalle.precio_unitario)) * Decimal(str(devolucion.cantidad_devuelta))
        impuesto_devuelto = Decimal(str(detalle.impuesto_unitario)) * Decimal(str(devolucion.cantidad_devuelta))
        
        venta.total += monto_devuelto
        venta.total_impuestos += impuesto_devuelto
        
        # Eliminar devolución
        db.session.delete(devolucion)
        set_net_payments(venta, {method: amount + refunds.get(method, 0) for method, amount in available.items()})
        db.session.expire(venta, ['devoluciones'])
        refresh_open_cash(employee_id, venta.sucursal_id)
        db.session.commit()
        
        return jsonify({
            'message': 'Devolución cancelada exitosamente',
            'nuevo_total_venta': float(venta.total)
        }), 200
    
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
