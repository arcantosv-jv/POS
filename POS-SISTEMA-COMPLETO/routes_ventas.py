from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Venta, DetalleVenta, Producto, Stock, Sucursal, PagoVenta, CierreCaja
from datetime import datetime, timedelta, date
from decimal import Decimal
import uuid
from config import get_cdmx_now

ventas_bp = Blueprint('ventas', __name__, url_prefix='/api/ventas')

@ventas_bp.route('', methods=['POST'])
@jwt_required()
def crear_venta():
    """Crear nueva venta (carrito de compra)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Empleados y admin pueden crear ventas
        if user.role not in ['employee', 'admin']:
            return jsonify({'error': 'Acceso denegado'}), 403
        
        data = request.get_json()
        
        # Validaciones
        if not data.get('detalles') or len(data['detalles']) == 0:
            return jsonify({'error': 'La venta debe tener al menos un producto'}), 400
        
        if not data.get('forma_pago'):
            return jsonify({'error': 'Forma de pago es requerida'}), 400
        
        # Generar número de venta
        numero_venta = f"V-{get_cdmx_now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8]}"
        
        # Crear venta
        venta = Venta(
            numero_venta=numero_venta,
            sucursal_id=user.sucursal_id,
            cajero_id=user_id,
            forma_pago=data['forma_pago'],
            observaciones=data.get('observaciones')
        )
        
        total_venta = Decimal('0.00')
        total_impuestos = Decimal('0.00')
        
        # Procesar detalles
        for detalle_data in data['detalles']:
            producto_id = detalle_data.get('producto_id')
            cantidad = int(detalle_data.get('cantidad', 0))
            precio_override = detalle_data.get('precio')  # Precio personalizado desde frontend
            
            if cantidad <= 0:
                return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400
            
            # Obtener producto
            producto = Producto.query.get(producto_id)
            if not producto:
                return jsonify({'error': f'Producto {producto_id} no encontrado'}), 404
            
            # Verificar stock disponible
            stock = Stock.query.filter_by(
                producto_id=producto_id,
                sucursal_id=user.sucursal_id
            ).first()
            
            # Determinar si hay stock disponible (sin restricción de rol)
            hay_stock = stock and stock.cantidad >= cantidad
            
            # Determinar precio unitario
            if precio_override is not None:
                # Usar precio personalizado del frontend (para productos sin precio fijo)
                precio_unitario = Decimal(str(precio_override))
            elif producto.precio is not None:
                # Usar precio del producto
                precio_unitario = Decimal(str(producto.precio))
            else:
                # Producto sin precio y sin override
                return jsonify({'error': f'El producto {producto.nombre} no tiene precio configurado'}), 400
            
            impuesto_unitario = (precio_unitario * Decimal(str(producto.impuesto))) / Decimal('100')
            subtotal = precio_unitario * Decimal(str(cantidad))
            
            # Crear detalle - Marcar sin_stock si no hay disponibilidad
            detalle = DetalleVenta(
                producto_id=producto_id,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                impuesto_unitario=impuesto_unitario,
                subtotal=subtotal,
                sin_stock=not hay_stock  # Marcar silenciosamente si fue sin stock
            )
            
            venta.detalles.append(detalle)
            
            # Descontar del stock SOLO si hay disponible
            if hay_stock:
                stock.cantidad -= cantidad
            
            
            
            # Acumular totales
            total_venta += subtotal
            total_impuestos += (impuesto_unitario * Decimal(str(cantidad)))
        
        venta.total = total_venta
        venta.total_impuestos = total_impuestos
        
        db.session.add(venta)
        db.session.flush()  # Para obtener el ID de la venta
        
        # Si es pago mixto, registrar desglose de pagos
        if data.get('forma_pago') == 'mixto' and data.get('pagos_mixtos'):
            pagos_mixtos = data.get('pagos_mixtos')
            for metodo, monto in pagos_mixtos.items():
                if monto and monto > 0:
                    pago = PagoVenta(
                        venta_id=venta.id,
                        metodo_pago=metodo,
                        monto=Decimal(str(monto))
                    )
                    db.session.add(pago)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Venta registrada exitosamente',
            'venta': venta.to_dict(include_detalles=True)
        }), 201
    
    except ValueError as e:
        return jsonify({'error': f'Valor inválido: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@ventas_bp.route('/validar-stock/<producto_id>', methods=['GET'])
@jwt_required()
def validar_stock(producto_id):
    """Validar disponibilidad de stock para un producto"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        cantidad_solicitada = request.args.get('cantidad', 1, type=int)
        
        # Obtener producto
        producto = Producto.query.get(producto_id)
        if not producto:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        # Verificar stock en la sucursal
        stock = Stock.query.filter_by(
            producto_id=producto_id,
            sucursal_id=user.sucursal_id
        ).first()
        
        cantidad_disponible = stock.cantidad if stock else 0
        hay_stock = cantidad_disponible >= cantidad_solicitada
        
        return jsonify({
            'producto_id': producto_id,
            'producto_nombre': producto.nombre,
            'cantidad_solicitada': cantidad_solicitada,
            'cantidad_disponible': cantidad_disponible,
            'hay_stock': hay_stock,
            'falta': max(0, cantidad_solicitada - cantidad_disponible)
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ventas_bp.route('', methods=['GET'])
@jwt_required()
def get_ventas():
    """Obtener ventas con filtros"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        sucursal_id = request.args.get('sucursal_id')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        query = Venta.query
        
        # Filtrar por sucursal
        if user.role == 'employee':
            query = query.filter_by(sucursal_id=user.sucursal_id)
        elif sucursal_id:
            query = query.filter_by(sucursal_id=sucursal_id)
        
        # Filtrar por fechas
        if fecha_inicio:
            query = query.filter(Venta.created_at >= datetime.fromisoformat(fecha_inicio))
        if fecha_fin:
            query = query.filter(Venta.created_at <= datetime.fromisoformat(fecha_fin))
        
        ventas = query.order_by(Venta.created_at.desc()).paginate(
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'total': ventas.total,
            'pages': ventas.pages,
            'current_page': page,
            'ventas': [v.to_dict() for v in ventas.items]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ventas_bp.route('/<venta_id>', methods=['GET'])
@jwt_required()
def get_venta(venta_id):
    """Obtener detalle de venta"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        venta = Venta.query.get(venta_id)
        if not venta:
            return jsonify({'error': 'Venta no encontrada'}), 404
        
        # Verificar acceso: admin ve todo, empleado solo su sucursal
        if user.role == 'employee' and venta.sucursal_id != user.sucursal_id:
            return jsonify({'error': 'Acceso denegado'}), 403
        
        return jsonify(venta.to_dict(include_detalles=True)), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ventas_bp.route('/<venta_id>/ticket', methods=['GET'])
@jwt_required()
def get_ticket(venta_id):
    """Obtener datos formateados para impresión de ticket"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        venta = Venta.query.get(venta_id)
        if not venta:
            return jsonify({'error': 'Venta no encontrada'}), 404
        
        # Verificar acceso
        if user.role == 'employee' and venta.sucursal_id != user.sucursal_id:
            return jsonify({'error': 'Acceso denegado'}), 403
        
        # Formatear ticket
        ticket = {
            'numero_venta': venta.numero_venta,
            'sucursal': venta.sucursal.nombre,
            'direccion': venta.sucursal.direccion,
            'telefono': venta.sucursal.telefono,
            'fecha': venta.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'cajero': venta.cajero.username,
            'detalles': [],
            'subtotal': 0,
            'total_impuestos': float(venta.total_impuestos),
            'total': float(venta.total),
            'forma_pago': venta.forma_pago
        }
        
        subtotal = 0
        for detalle in venta.detalles:
            detalle_dict = {
                'producto': detalle.producto.nombre,
                'cantidad': detalle.cantidad,
                'precio_unitario': float(detalle.precio_unitario),
                'subtotal': float(detalle.subtotal)
            }
            ticket['detalles'].append(detalle_dict)
            subtotal += float(detalle.subtotal)
        
        ticket['subtotal'] = subtotal
        
        return jsonify(ticket), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ventas_bp.route('/del-dia/resumen', methods=['GET'])
@jwt_required()
def get_ventas_del_dia():
    """Obtener ventas del día actual del empleado con desglose de pagos"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Solo empleados pueden ver sus ventas del día
        if user.role != 'employee':
            return jsonify({'error': 'Solo empleados pueden acceder a este endpoint'}), 403
        
        # Obtener inicio y fin del día actual (CDMX)
        hoy = get_cdmx_now().replace(hour=0, minute=0, second=0, microsecond=0)
        manana = hoy + timedelta(days=1)
        
        # Obtener ventas del día del empleado
        ventas = Venta.query.filter(
            Venta.cajero_id == user_id,
            Venta.created_at >= hoy,
            Venta.created_at < manana
        ).order_by(Venta.created_at.desc()).all()
        
        # Construir respuesta con desglose
        ventas_list = []
        totales = {
            'efectivo': 0,
            'tarjeta': 0,
            'transferencia': 0,
            'total': 0
        }
        
        for venta in ventas:
            venta_data = venta.to_dict(include_detalles=True)
            
            # Obtener detalles de pago
            if venta.pagos:
                # Si hay pagos registrados, usar esos
                pagos = [p.to_dict() for p in venta.pagos]
                venta_data['pagos'] = pagos
            else:
                # Si no, usar forma_pago única
                venta_data['pagos'] = [{
                    'metodo_pago': venta.forma_pago,
                    'monto': float(venta.total)
                }]
            
            # Acumular totales
            for pago in venta_data['pagos']:
                metodo = pago['metodo_pago'].lower()
                if metodo in totales:
                    totales[metodo] += pago['monto']
            totales['total'] += float(venta.total)
            
            ventas_list.append(venta_data)
        
        return jsonify({
            'ventas': ventas_list,
            'totales': totales,
            'cantidad_ventas': len(ventas),
            'fecha': hoy.isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ventas_bp.route('/<venta_id>/pagos', methods=['POST'])
@jwt_required()
def guardar_pagos_venta(venta_id):
    """Guardar o actualizar pagos mixtos de una venta"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Obtener venta
        venta = Venta.query.get(venta_id)
        if not venta:
            return jsonify({'error': 'Venta no encontrada'}), 404
        
        # Solo empleados de la misma sucursal o admin
        if user.role == 'employee' and venta.sucursal_id != user.sucursal_id:
            return jsonify({'error': 'Acceso denegado'}), 403
        
        data = request.get_json()
        pagos_data = data.get('pagos', [])
        
        if not pagos_data or len(pagos_data) == 0:
            return jsonify({'error': 'Debe proporcionar al menos un método de pago'}), 400
        
        # Calcular total de pagos
        total_pagos = Decimal('0.00')
        for pago in pagos_data:
            total_pagos += Decimal(str(pago.get('monto', 0)))
        
        # Verificar que el total de pagos coincida con el total de la venta
        if total_pagos != Decimal(str(venta.total)):
            return jsonify({
                'error': f'El total de pagos ({float(total_pagos)}) no coincide con el total de la venta ({float(venta.total)})'
            }), 400
        
        # Eliminar pagos existentes
        PagoVenta.query.filter_by(venta_id=venta_id).delete()
        
        # Crear nuevos pagos
        for pago_data in pagos_data:
            pago = PagoVenta(
                venta_id=venta_id,
                metodo_pago=pago_data.get('metodo_pago'),
                monto=Decimal(str(pago_data.get('monto', 0)))
            )
            db.session.add(pago)
        
        db.session.commit()
        
        # Retornar venta actualizada
        venta_actualizada = venta.to_dict(include_detalles=True)
        venta_actualizada['pagos'] = [p.to_dict() for p in venta.pagos]
        
        return jsonify({
            'message': 'Pagos guardados exitosamente',
            'venta': venta_actualizada
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============= ENDPOINTS CIERRE DE CAJA =============

@ventas_bp.route('/cierre-caja/hoy', methods=['GET'])
@jwt_required()
def get_cierre_caja_hoy():
    """Obtener cierre de caja del día actual del empleado"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.role != 'employee':
            return jsonify({'error': 'Solo empleados pueden acceder a esto'}), 403
        
        hoy = date.today()
        
        # Obtener cierre existente o crear uno
        cierre = CierreCaja.query.filter_by(
            empleado_id=user_id,
            fecha=hoy
        ).first()
        
        if not cierre:
            # Crear nuevo cierre de caja
            cierre = CierreCaja(
                empleado_id=user_id,
                sucursal_id=user.sucursal_id,
                fecha=hoy
            )
            db.session.add(cierre)
        
        # Calcular totales del día
        hoy_inicio = datetime.combine(hoy, datetime.min.time())
        hoy_fin = datetime.combine(hoy, datetime.max.time())
        
        ventas_hoy = Venta.query.filter(
            Venta.cajero_id == user_id,
            Venta.created_at >= hoy_inicio,
            Venta.created_at <= hoy_fin
        ).all()
        
        total_ventas = Decimal('0.00')
        total_efectivo = Decimal('0.00')
        total_tarjeta = Decimal('0.00')
        total_transferencia = Decimal('0.00')
        
        for venta in ventas_hoy:
            total_ventas += Decimal(str(venta.total))
            
            # Obtener detalles de pago
            if venta.pagos:
                for pago in venta.pagos:
                    metodo = pago.metodo_pago.lower()
                    monto = Decimal(str(pago.monto))
                    if metodo == 'efectivo':
                        total_efectivo += monto
                    elif metodo == 'tarjeta':
                        total_tarjeta += monto
                    elif metodo == 'transferencia':
                        total_transferencia += monto
            else:
                # Si no hay pagos registrados, usar forma_pago
                metodo = venta.forma_pago.lower()
                monto = Decimal(str(venta.total))
                if metodo == 'efectivo':
                    total_efectivo += monto
                elif metodo == 'tarjeta':
                    total_tarjeta += monto
                elif metodo == 'transferencia':
                    total_transferencia += monto
        
        cierre.total_ventas = total_ventas
        cierre.total_efectivo = total_efectivo
        cierre.total_tarjeta = total_tarjeta
        cierre.total_transferencia = total_transferencia
        
        db.session.commit()
        
        return jsonify(cierre.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@ventas_bp.route('/cierre-caja', methods=['POST'])
@jwt_required()
def crear_cierre_caja():
    """Crear/actualizar cierre de caja del empleado"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.role != 'employee':
            return jsonify({'error': 'Solo empleados pueden acceder a esto'}), 403
        
        data = request.get_json()
        hoy = date.today()
        
        # Obtener cierre existente
        cierre = CierreCaja.query.filter_by(
            empleado_id=user_id,
            fecha=hoy
        ).first()
        
        if not cierre:
            return jsonify({'error': 'Cierre de caja no encontrado'}), 404
        
        # Actualizar con datos reportados
        efectivo_reportado = Decimal(str(data.get('efectivo_reportado', 0)))
        cierre.efectivo_reportado = efectivo_reportado
        cierre.diferencia = efectivo_reportado - cierre.total_efectivo
        cierre.observaciones = data.get('observaciones', '')
        cierre.estado = 'cerrado'
        
        db.session.commit()
        
        return jsonify({
            'message': 'Cierre de caja registrado exitosamente',
            'cierre': cierre.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============= ENDPOINTS REPORTES (ADMIN) =============

@ventas_bp.route('/reportes/por-fecha', methods=['GET'])
@jwt_required()
def reportes_por_fecha():
    """Obtener reportes de ventas por rango de fechas (Admin)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.role != 'admin':
            return jsonify({'error': 'Solo admins pueden acceder a reportes'}), 403
        
        fecha_inicio_str = request.args.get('fecha_inicio')
        fecha_fin_str = request.args.get('fecha_fin')
        sucursal_id = request.args.get('sucursal_id')
        
        if not fecha_inicio_str or not fecha_fin_str:
            return jsonify({'error': 'Debe proporcionar fecha_inicio y fecha_fin'}), 400
        
        try:
            fecha_inicio = datetime.fromisoformat(fecha_inicio_str).date()
            fecha_fin = datetime.fromisoformat(fecha_fin_str).date()
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido (use YYYY-MM-DD)'}), 400
        
        # Convertir a datetime para comparación
        inicio = datetime.combine(fecha_inicio, datetime.min.time())
        fin = datetime.combine(fecha_fin, datetime.max.time())
        
        query = Venta.query.filter(
            Venta.created_at >= inicio,
            Venta.created_at <= fin
        )
        
        if sucursal_id:
            query = query.filter_by(sucursal_id=sucursal_id)
        
        ventas = query.order_by(Venta.created_at.desc()).all()
        
        # Calcular totales
        totales = {
            'efectivo': 0,
            'tarjeta': 0,
            'transferencia': 0,
            'total': 0,
            'cantidad_ventas': len(ventas)
        }
        
        ventas_list = []
        
        for venta in ventas:
            venta_data = venta.to_dict(include_detalles=True)
            
            # Obtener detalles de pago
            if venta.pagos:
                pagos = [p.to_dict() for p in venta.pagos]
                venta_data['pagos'] = pagos
            else:
                venta_data['pagos'] = [{
                    'metodo_pago': venta.forma_pago,
                    'monto': float(venta.total)
                }]
            
            # Acumular totales
            for pago in venta_data['pagos']:
                metodo = pago['metodo_pago'].lower()
                if metodo in totales:
                    totales[metodo] += pago['monto']
            totales['total'] += float(venta.total)
            
            ventas_list.append(venta_data)
        
        return jsonify({
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat(),
            'ventas': ventas_list,
            'totales': totales
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ventas_bp.route('/reportes/cierres-caja', methods=['GET'])
@jwt_required()
def reportes_cierres_caja():
    """Obtener reportes de cierres de caja (Admin)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.role != 'admin':
            return jsonify({'error': 'Solo admins pueden acceder a reportes'}), 403
        
        fecha_inicio_str = request.args.get('fecha_inicio')
        fecha_fin_str = request.args.get('fecha_fin')
        sucursal_id = request.args.get('sucursal_id')
        empleado_id = request.args.get('empleado_id')
        
        query = CierreCaja.query
        
        if fecha_inicio_str:
            try:
                fecha_inicio = datetime.fromisoformat(fecha_inicio_str).date()
                query = query.filter(CierreCaja.fecha >= fecha_inicio)
            except ValueError:
                pass
        
        if fecha_fin_str:
            try:
                fecha_fin = datetime.fromisoformat(fecha_fin_str).date()
                query = query.filter(CierreCaja.fecha <= fecha_fin)
            except ValueError:
                pass
        
        if sucursal_id:
            query = query.filter_by(sucursal_id=sucursal_id)
        
        if empleado_id:
            query = query.filter_by(empleado_id=empleado_id)
        
        cierres = query.order_by(CierreCaja.fecha.desc()).all()
        
        return jsonify({
            'cierres': [c.to_dict() for c in cierres],
            'cantidad': len(cierres)
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ventas_bp.route('/cierre-caja/corregir', methods=['POST'])
@jwt_required()
def corregir_cierre_caja():
    """Corregir/reabrirciembre de caja del empleado"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.role != 'employee':
            return jsonify({'error': 'Solo empleados pueden acceder a esto'}), 403
        
        data = request.get_json()
        hoy = date.today()
        
        # Obtener cierre existente
        cierre = CierreCaja.query.filter_by(
            empleado_id=user_id,
            fecha=hoy
        ).first()
        
        if not cierre:
            return jsonify({'error': 'Cierre de caja no encontrado'}), 404
        
        # Actualizar con datos reportados
        efectivo_reportado = Decimal(str(data.get('efectivo_reportado', 0)))
        cierre.efectivo_reportado = efectivo_reportado
        cierre.diferencia = efectivo_reportado - cierre.total_efectivo
        cierre.observaciones = data.get('observaciones', '')
        cierre.estado = 'cerrado'
        
        db.session.commit()
        
        return jsonify({
            'message': 'Cierre de caja corregido exitosamente',
            'cierre': cierre.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@ventas_bp.route('/sin-stock', methods=['GET'])
@jwt_required()
def get_ventas_sin_stock():
    """Obtener ventas realizadas sin stock disponible (ADMIN ONLY)"""
    try:
        from flask_jwt_extended import get_jwt
        claims = get_jwt()
        
        # Verificar que sea admin
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if user.role != 'admin':
            return jsonify({'error': 'Acceso denegado. Solo administradores'}), 403
        
        # Parámetros de filtro
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        sucursal_id = request.args.get('sucursal_id')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Query base: obtener detalles de venta con sin_stock=True
        query = db.session.query(
            DetalleVenta,
            Venta,
            Producto
        ).join(Venta, DetalleVenta.venta_id == Venta.id)\
         .join(Producto, DetalleVenta.producto_id == Producto.id)\
         .filter(DetalleVenta.sin_stock == True)
        
        # Aplicar filtros
        if fecha_inicio:
            query = query.filter(Venta.created_at >= datetime.fromisoformat(fecha_inicio))
        if fecha_fin:
            query = query.filter(Venta.created_at <= datetime.fromisoformat(fecha_fin))
        if sucursal_id:
            query = query.filter(Venta.sucursal_id == sucursal_id)
        
        # Ordenar por fecha descendente
        query = query.order_by(Venta.created_at.desc())
        
        # Paginar
        paginated = query.paginate(page=page, per_page=per_page)
        
        # Construir respuesta
        ventas_sin_stock = []
        for detalle, venta, producto in paginated.items:
            ventas_sin_stock.append({
                'detalle_id': detalle.id,
                'venta_id': venta.id,
                'numero_venta': venta.numero_venta,
                'producto_id': producto.id,
                'producto_nombre': producto.nombre,
                'producto_codigo': producto.codigo,
                'cantidad_vendida': detalle.cantidad,
                'costo_unitario': float(detalle.precio_unitario),
                'costo_total': float(detalle.subtotal),
                'fecha_venta': venta.created_at.isoformat(),
                'sucursal': venta.sucursal.nombre,
                'cajero': venta.cajero.username
            })
        
        return jsonify({
            'ventas_sin_stock': ventas_sin_stock,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages
            }
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
