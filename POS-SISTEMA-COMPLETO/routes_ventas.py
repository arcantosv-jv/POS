from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Venta, DetalleVenta, Producto, Stock, Sucursal, PagoVenta, CierreCaja
from datetime import datetime, timedelta, date
from decimal import Decimal
from business_validation import money, text_value
from cash_accounting import refresh_cash, lock_branch, cierres_confirmados, actualizar_arrastres, movimientos_pendientes
import uuid
from config import get_cdmx_now, CDMX_TZ

ventas_bp = Blueprint('ventas', __name__, url_prefix='/api/ventas')

@ventas_bp.route('', methods=['POST'])
@jwt_required()
def crear_venta():
    """Crear nueva venta (carrito de compra)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.filter_by(id=user_id).with_for_update().first()
        lock_branch(user.sucursal_id)
        
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
            # convertir fecha ISO a datetime en timezone CDMX
            d = datetime.fromisoformat(fecha_inicio).date()
            inicio = CDMX_TZ.localize(datetime.combine(d, datetime.min.time()))
            query = query.filter(Venta.created_at >= inicio)
        if fecha_fin:
            d = datetime.fromisoformat(fecha_fin).date()
            fin = CDMX_TZ.localize(datetime.combine(d, datetime.max.time()))
            query = query.filter(Venta.created_at <= fin)
        
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
        
        if any(d.reembolsos is not None for d in venta.devoluciones):
            return jsonify({'error': 'Esta venta tiene reembolsos registrados; no se puede reemplazar su desglose de pagos'}), 409

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

def plazo_correccion(cierre):
    if cierre.estado != 'cerrado' or not cierre.closed_at:
        return None, False
    confirmado = cierre.closed_at
    if confirmado.tzinfo is None:
        confirmado = CDMX_TZ.localize(confirmado)
    limite = confirmado + timedelta(hours=1)
    ahora = get_cdmx_now()
    return limite, confirmado <= ahora <= limite


def detalle_cierre(cierre):
    ventas = (movimientos_pendientes(cierre)[0] if cierre.estado == 'abierto' else
              Venta.query.filter_by(cierre_caja_id=cierre.id).order_by(Venta.created_at.desc()).all())

    productos = {}
    for venta in ventas:
        for detalle in venta.detalles:
            producto = productos.setdefault(detalle.producto_id, {
                'producto_id': detalle.producto_id,
                'codigo': detalle.producto.codigo,
                'producto': detalle.producto.nombre,
                'unidades': 0,
                'ingresos_brutos': Decimal('0.00')
            })
            producto['unidades'] += detalle.cantidad
            producto['ingresos_brutos'] += detalle.subtotal

    datos_cierre = cierre.to_dict()
    limite, vigente = plazo_correccion(cierre)
    datos_cierre['editable_hasta'] = limite.isoformat() if limite else None
    datos_cierre['puede_corregir'] = vigente and cierre.empleado_id == get_jwt_identity()
    datos_cierre.update({
        'cantidad_ventas': len(ventas),
        'total_vendido': float(cierre.total_ventas or 0),
        'productos': [
            {**producto, 'ingresos_brutos': float(producto['ingresos_brutos'])}
            for producto in sorted(productos.values(), key=lambda item: item['unidades'], reverse=True)
        ]
    })
    return datos_cierre


def cierre_con_contexto(cierre):
    confirmados = cierres_confirmados(cierre.sucursal_id, cierre.fecha)
    anteriores = confirmados
    if cierre.estado == 'cerrado':
        anteriores = confirmados[:next(i for i, c in enumerate(confirmados) if c.id == cierre.id)]
    datos = detalle_cierre(cierre)
    datos['numero_turno'] = len(anteriores) + 1
    datos['cierres_anteriores'] = [dict(detalle_cierre(c), numero_turno=i + 1) for i, c in enumerate(anteriores)]
    recientes = CierreCaja.query.filter_by(empleado_id=get_jwt_identity(), sucursal_id=cierre.sucursal_id,
        fecha=get_cdmx_now().date() - timedelta(days=1), estado='cerrado').all()
    datos['cierres_editables_dia_anterior'] = [detalle_cierre(c) for c in recientes if plazo_correccion(c)[1]]
    return datos


def cierres_del_dia(user):
    return CierreCaja.query.filter_by(empleado_id=user.id, sucursal_id=user.sucursal_id, fecha=get_cdmx_now().date())


def cierre_abierto(user):
    return cierres_del_dia(user).filter_by(estado='abierto').order_by(CierreCaja.created_at.desc(), CierreCaja.id.desc()).first()


def nuevo_cierre(user):
    cierre = CierreCaja(empleado_id=user.id, sucursal_id=user.sucursal_id,
                        fecha=get_cdmx_now().date(), estado='abierto')
    db.session.add(cierre)
    db.session.flush()
    return cierre


@ventas_bp.route('/cierre-caja/hoy', methods=['GET'])
@jwt_required()
def get_cierre_caja_hoy():
    try:
        user = User.query.filter_by(id=get_jwt_identity()).with_for_update().first()
        lock_branch(user.sucursal_id)
        if user.role != 'employee':
            return jsonify({'error': 'Solo empleados pueden acceder a esto'}), 403
        cierre = cierre_abierto(user) or cierres_del_dia(user).order_by(CierreCaja.created_at.desc(), CierreCaja.id.desc()).first()
        if not cierre:
            cierre = nuevo_cierre(user)
        if cierre.estado == 'abierto':
            refresh_cash(cierre)
        db.session.commit()
        return jsonify(cierre_con_contexto(cierre)), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@ventas_bp.route('/cierre-caja/nuevo', methods=['POST'])
@jwt_required()
def iniciar_nuevo_cierre():
    try:
        user = User.query.filter_by(id=get_jwt_identity()).with_for_update().first()
        lock_branch(user.sucursal_id)
        if user.role != 'employee':
            return jsonify({'error': 'Solo empleados pueden iniciar un cierre'}), 403
        # Repetir la solicitud nunca crea dos cajas abiertas.
        cierre = cierre_abierto(user) or nuevo_cierre(user)
        refresh_cash(cierre)
        db.session.commit()
        return jsonify({'cierre': cierre_con_contexto(cierre)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def validar_datos_cierre(data, cierre):
    efectivo = money(data.get('efectivo_reportado', 0), 'Efectivo reportado')
    if 'egresos' in data:
        entries = data['egresos']
    elif 'egreso' in data or 'concepto_egreso' in data:
        monto = money(data.get('egreso', cierre.egreso or 0) or 0, 'Egreso')
        entries = [{'monto': monto, 'concepto': data.get('concepto_egreso', cierre.concepto_egreso or '')}] if monto else []
    else:
        entries = cierre.to_dict()['egresos']
    if not isinstance(entries, list) or len(entries) > 100:
        raise ValueError('Los egresos deben ser una lista de máximo 100 movimientos')
    egresos = []
    total = Decimal('0')
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('Egreso inválido')
        monto = money(entry.get('monto'), 'Egreso')
        if monto <= 0:
            raise ValueError('Cada egreso debe ser mayor a cero; elimina los renglones vacíos')
        concepto = text_value(entry.get('concepto', ''), 'Concepto del egreso', required=True)
        comprobante = text_value(entry.get('comprobante', ''), 'Referencia de comprobante', 500)
        total += monto
        egresos.append({'monto': str(monto), 'concepto': concepto, 'comprobante': comprobante})
    money(total, 'Total de egresos')
    return efectivo, total, '\n'.join(e['concepto'] for e in egresos) or None, egresos


@ventas_bp.route('/cierre-caja', methods=['POST'])
@jwt_required()
def crear_cierre_caja():
    """Crear/actualizar cierre de caja del empleado"""
    try:
        user_id = get_jwt_identity()
        user = User.query.filter_by(id=user_id).with_for_update().first()
        lock_branch(user.sucursal_id)
        
        if user.role != 'employee':
            return jsonify({'error': 'Solo empleados pueden acceder a esto'}), 403
        
        data = request.get_json() or {}
        cierre = (cierres_del_dia(user).filter_by(id=data['cierre_id']).first()
                  if data.get('cierre_id') else cierre_abierto(user))
        if not cierre:
            return jsonify({'error': 'No hay un cierre abierto. Inicia un nuevo cierre.'}), 409
        if cierre.estado != 'abierto':
            return jsonify({'error': 'Este cierre ya fue confirmado. Usa la opción de corregir.'}), 409

        # Actualizar con datos reportados
        try:
            efectivo_reportado, egreso, concepto, egresos = validar_datos_cierre(data, cierre)
        except ValueError as error:
            return jsonify({'error': str(error)}), 400
        sales, refunds = refresh_cash(cierre)
        for sale in sales:
            sale.cierre_caja_id = cierre.id
        for refund in refunds:
            refund.cierre_caja_id = cierre.id
        cierre.egresos = egresos
        cierre.egreso = egreso
        cierre.concepto_egreso = concepto
        cierre.efectivo_reportado = efectivo_reportado
        cierre.diferencia = efectivo_reportado - cierre.efectivo_esperado
        cierre.observaciones = data.get('observaciones', '')
        cierre.estado = 'cerrado'
        cierre.closed_at = get_cdmx_now()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Cierre de caja registrado exitosamente',
            'cierre': cierre_con_contexto(cierre)
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


@ventas_bp.route('/reportes/cierres-caja-detalle', methods=['GET'])
@jwt_required()
def reportes_cierres_caja_detalle():
    """Consultar cierres confirmados y productos vendidos por empleado/caja."""
    try:
        user = User.query.get(get_jwt_identity())
        if not user or user.role != 'admin':
            return jsonify({'error': 'Solo administradores pueden consultar cierres de caja'}), 403

        fecha_inicio_str = request.args.get('fecha_inicio')
        fecha_fin_str = request.args.get('fecha_fin')
        sucursal_id = request.args.get('sucursal_id') or None
        if not fecha_inicio_str or not fecha_fin_str:
            return jsonify({'error': 'Debe proporcionar fecha_inicio y fecha_fin'}), 400

        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido (use YYYY-MM-DD)'}), 400

        if fecha_inicio > fecha_fin:
            return jsonify({'error': 'La fecha inicial no puede ser posterior a la fecha final'}), 400
        if (fecha_fin - fecha_inicio).days > 365:
            return jsonify({'error': 'El rango máximo es de 366 días'}), 400

        query = CierreCaja.query.filter(
            CierreCaja.estado == 'cerrado',
            CierreCaja.fecha >= fecha_inicio,
            CierreCaja.fecha <= fecha_fin
        )
        if sucursal_id:
            if not Sucursal.query.get(sucursal_id):
                return jsonify({'error': 'Sucursal no encontrada'}), 404
            query = query.filter(CierreCaja.sucursal_id == sucursal_id)

        cierres = query.order_by(CierreCaja.fecha.desc(), CierreCaja.closed_at.desc()).all()

        resultado = []
        for cierre in cierres:
            resultado.append(detalle_cierre(cierre))

        return jsonify({
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat(),
            'sucursal_id': sucursal_id,
            'cantidad': len(resultado),
            'cierres': resultado
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@ventas_bp.route('/cierre-caja/corregir', methods=['POST'])
@jwt_required()
def corregir_cierre_caja():
    """Corregir un cierre propio durante la hora posterior a su confirmación."""
    try:
        user_id = get_jwt_identity()
        user = User.query.filter_by(id=user_id).with_for_update().first()
        lock_branch(user.sucursal_id)
        
        if user.role != 'employee':
            return jsonify({'error': 'Solo empleados pueden acceder a esto'}), 403
        
        data = request.get_json() or {}
        if data.get('cierre_id'):
            cierre = CierreCaja.query.filter_by(empleado_id=user.id, sucursal_id=user.sucursal_id, id=data['cierre_id'], estado='cerrado').first()
        else:
            candidates = cierres_del_dia(user).filter_by(estado='cerrado').all()
            cierre = candidates[0] if len(candidates) == 1 else None
        if not cierre:
            return jsonify({'error': 'Selecciona el cierre confirmado que deseas corregir'}), 400
        if not plazo_correccion(cierre)[1]:
            return jsonify({'error': 'Solo puedes modificar el cierre hasta una hora después de su confirmación original.'}), 409

        # Actualizar con datos reportados
        try:
            efectivo_reportado, egreso, concepto, egresos = validar_datos_cierre(data, cierre)
        except ValueError as error:
            return jsonify({'error': str(error)}), 400
        cierre.egresos = egresos
        cierre.egreso = egreso
        cierre.concepto_egreso = concepto
        cierre.efectivo_reportado = efectivo_reportado
        cierre.diferencia = efectivo_reportado - cierre.efectivo_esperado
        cierre.observaciones = data.get('observaciones', '')
        cierre.estado = 'cerrado'
        actualizar_arrastres(cierre.sucursal_id, cierre.fecha)
        # Conservar la hora original de confirmación y sus movimientos.
        
        db.session.commit()
        
        return jsonify({
            'message': 'Cierre de caja corregido exitosamente',
            'cierre': cierre_con_contexto(cierre)
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
            d = datetime.fromisoformat(fecha_inicio).date()
            inicio = CDMX_TZ.localize(datetime.combine(d, datetime.min.time()))
            query = query.filter(Venta.created_at >= inicio)
        if fecha_fin:
            d = datetime.fromisoformat(fecha_fin).date()
            fin = CDMX_TZ.localize(datetime.combine(d, datetime.max.time()))
            query = query.filter(Venta.created_at <= fin)
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
