from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Venta, DetalleVenta, EntradaInventario, Sucursal, Stock, Producto
from sqlalchemy import func
from datetime import datetime, timedelta
from decimal import Decimal
from config import get_cdmx_now, CDMX_TZ

reportes_bp = Blueprint('reportes', __name__, url_prefix='/api/reportes')

@reportes_bp.route('/ventas-diarias', methods=['GET'])
@jwt_required()
def reportes_ventas_diarias():
    """Reporte de ventas diarias"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        sucursal_id = request.args.get('sucursal_id')
        fecha = request.args.get('fecha')  # YYYY-MM-DD
        
        if not fecha:
            fecha = get_cdmx_now().strftime('%Y-%m-%d')
        
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
        fecha_siguiente = fecha_obj + timedelta(days=1)

        inicio = CDMX_TZ.localize(datetime.combine(fecha_obj.date(), datetime.min.time()))
        fin = CDMX_TZ.localize(datetime.combine(fecha_siguiente.date(), datetime.min.time()))

        query = Venta.query.filter(
            Venta.created_at >= inicio,
            Venta.created_at < fin
        )
        
        # Filtrar por sucursal
        if user.role == 'employee':
            query = query.filter_by(sucursal_id=user.sucursal_id)
        elif sucursal_id:
            query = query.filter_by(sucursal_id=sucursal_id)
        
        ventas = query.all()
        
        total_ventas = float(sum(v.total for v in ventas))
        total_impuestos = float(sum(v.total_impuestos for v in ventas))
        cantidad_transacciones = len(ventas)
        
        # Agrupar por forma de pago
        por_forma_pago = {}
        for venta in ventas:
            forma_pago = venta.forma_pago
            if forma_pago not in por_forma_pago:
                por_forma_pago[forma_pago] = Decimal('0.00')
            por_forma_pago[forma_pago] += venta.total
        
        return jsonify({
            'fecha': fecha,
            'sucursal_id': sucursal_id,
            'total_ventas': total_ventas,
            'total_impuestos': total_impuestos,
            'cantidad_transacciones': cantidad_transacciones,
            'promedio_venta': float(total_ventas / cantidad_transacciones) if cantidad_transacciones > 0 else 0,
            'por_forma_pago': {k: float(v) for k, v in por_forma_pago.items()},
            'detalles_ventas': [v.to_dict() for v in ventas]
        }), 200
    
    except ValueError:
        return jsonify({'error': 'Formato de fecha inválido (use YYYY-MM-DD)'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reportes_bp.route('/ventas-mensuales', methods=['GET'])
@jwt_required()
def reportes_ventas_mensuales():
    """Reporte de ventas mensuales"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        sucursal_id = request.args.get('sucursal_id')
        mes = request.args.get('mes')  # YYYY-MM
        
        if not mes:
            mes = get_cdmx_now().strftime('%Y-%m')
        
        # Parsear mes
        fecha_inicio = datetime.strptime(mes, '%Y-%m')
        if fecha_inicio.month == 12:
            fecha_fin = datetime(fecha_inicio.year + 1, 1, 1)
        else:
            fecha_fin = datetime(fecha_inicio.year, fecha_inicio.month + 1, 1)
        inicio = CDMX_TZ.localize(datetime.combine(fecha_inicio.date(), datetime.min.time()))
        fin = CDMX_TZ.localize(datetime.combine(fecha_fin.date(), datetime.min.time()))

        query = Venta.query.filter(
            Venta.created_at >= inicio,
            Venta.created_at < fin
        )
        
        # Filtrar por sucursal
        if user.role == 'employee':
            query = query.filter_by(sucursal_id=user.sucursal_id)
        elif sucursal_id:
            query = query.filter_by(sucursal_id=sucursal_id)
        
        ventas = query.all()
        
        total_ventas = float(sum(v.total for v in ventas))
        total_impuestos = float(sum(v.total_impuestos for v in ventas))
        cantidad_transacciones = len(ventas)
        
        # Datos diarios
        ventas_por_dia = {}
        for venta in ventas:
            dia = venta.created_at.strftime('%Y-%m-%d')
            if dia not in ventas_por_dia:
                ventas_por_dia[dia] = {
                    'total': Decimal('0.00'),
                    'cantidad': 0,
                    'impuestos': Decimal('0.00')
                }
            ventas_por_dia[dia]['total'] += venta.total
            ventas_por_dia[dia]['cantidad'] += 1
            ventas_por_dia[dia]['impuestos'] += venta.total_impuestos
        
        # Convertir a float
        ventas_por_dia_float = {}
        for dia, datos in ventas_por_dia.items():
            ventas_por_dia_float[dia] = {
                'total': float(datos['total']),
                'cantidad': datos['cantidad'],
                'impuestos': float(datos['impuestos'])
            }
        
        return jsonify({
            'mes': mes,
            'sucursal_id': sucursal_id,
            'total_ventas': total_ventas,
            'total_impuestos': total_impuestos,
            'cantidad_transacciones': cantidad_transacciones,
            'promedio_diario': float(total_ventas / len(ventas_por_dia)) if ventas_por_dia else 0,
            'promedio_venta': float(total_ventas / cantidad_transacciones) if cantidad_transacciones > 0 else 0,
            'ventas_por_dia': ventas_por_dia_float
        }), 200
    
    except ValueError:
        return jsonify({'error': 'Formato de mes inválido (use YYYY-MM)'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reportes_bp.route('/ventas-anuales', methods=['GET'])
@jwt_required()
def reportes_ventas_anuales():
    """Reporte de ventas anuales"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        sucursal_id = request.args.get('sucursal_id')
        año = request.args.get('año', type=int)
        
        if not año:
            año = get_cdmx_now().year
        
        fecha_inicio = datetime(año, 1, 1)
        fecha_fin = datetime(año + 1, 1, 1)

        inicio = CDMX_TZ.localize(datetime.combine(fecha_inicio.date(), datetime.min.time()))
        fin = CDMX_TZ.localize(datetime.combine(fecha_fin.date(), datetime.min.time()))

        query = Venta.query.filter(
            Venta.created_at >= inicio,
            Venta.created_at < fin
        )
        
        # Filtrar por sucursal
        if user.role == 'employee':
            query = query.filter_by(sucursal_id=user.sucursal_id)
        elif sucursal_id:
            query = query.filter_by(sucursal_id=sucursal_id)
        
        ventas = query.all()
        
        total_ventas = float(sum(v.total for v in ventas))
        total_impuestos = float(sum(v.total_impuestos for v in ventas))
        cantidad_transacciones = len(ventas)
        
        # Datos mensuales
        ventas_por_mes = {}
        for venta in ventas:
            mes = venta.created_at.strftime('%Y-%m')
            if mes not in ventas_por_mes:
                ventas_por_mes[mes] = {
                    'total': Decimal('0.00'),
                    'cantidad': 0,
                    'impuestos': Decimal('0.00')
                }
            ventas_por_mes[mes]['total'] += venta.total
            ventas_por_mes[mes]['cantidad'] += 1
            ventas_por_mes[mes]['impuestos'] += venta.total_impuestos
        
        # Convertir a float
        ventas_por_mes_float = {}
        for mes, datos in ventas_por_mes.items():
            ventas_por_mes_float[mes] = {
                'total': float(datos['total']),
                'cantidad': datos['cantidad'],
                'impuestos': float(datos['impuestos'])
            }
        
        return jsonify({
            'año': año,
            'sucursal_id': sucursal_id,
            'total_ventas': total_ventas,
            'total_impuestos': total_impuestos,
            'cantidad_transacciones': cantidad_transacciones,
            'promedio_mensual': float(total_ventas / len(ventas_por_mes)) if ventas_por_mes else 0,
            'promedio_venta': float(total_ventas / cantidad_transacciones) if cantidad_transacciones > 0 else 0,
            'ventas_por_mes': ventas_por_mes_float
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reportes_bp.route('/productos-vendidos', methods=['GET'])
@jwt_required()
def reportes_productos_vendidos():
    """Reporte de productos más vendidos"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        sucursal_id = request.args.get('sucursal_id')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        query = DetalleVenta.query.join(Venta)
        
        # Filtrar por sucursal
        if user.role == 'employee':
            query = query.filter(Venta.sucursal_id == user.sucursal_id)
        elif sucursal_id:
            query = query.filter(Venta.sucursal_id == sucursal_id)
        
        # Filtrar por fechas
        if fecha_inicio:
            d = datetime.fromisoformat(fecha_inicio).date()
            inicio = CDMX_TZ.localize(datetime.combine(d, datetime.min.time()))
            query = query.filter(Venta.created_at >= inicio)
        if fecha_fin:
            d = datetime.fromisoformat(fecha_fin).date()
            fin = CDMX_TZ.localize(datetime.combine(d, datetime.max.time()))
            query = query.filter(Venta.created_at <= fin)
        
        detalles = query.all()
        
        # Agrupar por producto
        productos = {}
        for detalle in detalles:
            producto_id = detalle.producto_id
            if producto_id not in productos:
                productos[producto_id] = {
                    'nombre': detalle.producto.nombre,
                    'codigo': detalle.producto.codigo,
                    'cantidad_total': 0,
                    'ingresos_total': Decimal('0.00')
                }
            
            productos[producto_id]['cantidad_total'] += detalle.cantidad
            productos[producto_id]['ingresos_total'] += detalle.subtotal
        
        # Ordenar por cantidad vendida
        productos_ordenados = sorted(
            productos.items(),
            key=lambda x: x[1]['cantidad_total'],
            reverse=True
        )
        
        resultado = []
        for producto_id, datos in productos_ordenados:
            resultado.append({
                'id': producto_id,
                'nombre': datos['nombre'],
                'codigo': datos['codigo'],
                'cantidad': datos['cantidad_total'],
                'ingresos': float(datos['ingresos_total']),
                'promedio_venta': float(datos['ingresos_total'] / datos['cantidad_total']) if datos['cantidad_total'] > 0 else 0
            })
        
        return jsonify(resultado), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reportes_bp.route('/consolidado-sucursales', methods=['GET'])
@jwt_required()
def reporte_consolidado():
    """Reporte consolidado de todas las sucursales (solo admin)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.role != 'admin':
            return jsonify({'error': 'Solo admin puede ver reportes consolidados'}), 403
        
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        query = Venta.query
        
        if fecha_inicio:
            query = query.filter(Venta.created_at >= datetime.fromisoformat(fecha_inicio))
        if fecha_fin:
            query = query.filter(Venta.created_at <= datetime.fromisoformat(fecha_fin))
        
        ventas = query.all()
        
        # Agrupar por sucursal
        por_sucursal = {}
        for venta in ventas:
            sucursal_id = venta.sucursal_id
            if sucursal_id not in por_sucursal:
                por_sucursal[sucursal_id] = {
                    'sucursal': venta.sucursal.nombre,
                    'total': Decimal('0.00'),
                    'impuestos': Decimal('0.00'),
                    'transacciones': 0
                }
            
            por_sucursal[sucursal_id]['total'] += venta.total
            por_sucursal[sucursal_id]['impuestos'] += venta.total_impuestos
            por_sucursal[sucursal_id]['transacciones'] += 1
        
        # Convertir a float
        resultado = {}
        total_general = Decimal('0.00')
        total_impuestos_general = Decimal('0.00')
        
        for sucursal_id, datos in por_sucursal.items():
            resultado[sucursal_id] = {
                'sucursal': datos['sucursal'],
                'sucursal_id': sucursal_id,
                'total': float(datos['total']),
                'impuestos': float(datos['impuestos']),
                'cantidad': datos['transacciones'],
                'promedio': float(datos['total'] / datos['transacciones']) if datos['transacciones'] > 0 else 0
            }
            total_general += datos['total']
            total_impuestos_general += datos['impuestos']
        
        return jsonify({
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'por_sucursal': resultado,
            'total_general': float(total_general),
            'total_impuestos_general': float(total_impuestos_general),
            'cantidad_transacciones_general': len(ventas)
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reportes_bp.route('/productos-bajo-stock', methods=['GET'])
@jwt_required()
def reportes_productos_bajo_stock():
    """Contar PRODUCTOS ACTIVOS ÚNICOS con stock bajo (cantidad < cantidad_minima)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # JOIN entre Stock y Producto para filtrar por activos
        query = db.session.query(Stock).join(Producto, Stock.producto_id == Producto.id)
        query = query.filter(Producto.is_active == True)
        
        # Si es empleado, filtrar por su sucursal
        if user.role == 'employee' and user.sucursal_id:
            query = query.filter(Stock.sucursal_id == user.sucursal_id)
        
        # Contar PRODUCTOS ACTIVOS ÚNICOS donde cantidad < cantidad_minima
        bajo_stock = query.filter(Stock.cantidad < Stock.cantidad_minima).distinct(Stock.producto_id).count()
        
        # Contar también items totales en bajo stock (para referencia)
        items_bajo_stock = query.filter(Stock.cantidad < Stock.cantidad_minima).count()
        
        return jsonify({
            'cantidad_bajo_stock': bajo_stock,
            'items_bajo_stock': items_bajo_stock
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reportes_bp.route('/total-productos', methods=['GET'])
@jwt_required()
def reportes_total_productos():
    """Contar total de productos activos"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Contar productos activos
        query = Producto.query.filter_by(is_active=True)
        
        # Si es empleado, contar solo productos que tienen stock en su sucursal
        if user.role == 'employee' and user.sucursal_id:
            query = query.join(Stock).filter(Stock.sucursal_id == user.sucursal_id).distinct()
        
        total = query.count()
        
        return jsonify({
            'total_productos': total
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
