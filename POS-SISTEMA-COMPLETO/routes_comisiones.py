from permissions import delegated_access, current_branch, can
"""Registro independiente de comisiones; sin movimientos de ventas o caja."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Comision, Venta, DetalleVenta, EmpleadoComision
from datetime import date
from sqlalchemy import func, case
from sqlalchemy.exc import IntegrityError
from comisiones_ventas import INICIO, rango, fecha_cdmx, tipo_dispositivo, unidades_disponibles, datos_unidad
from routes_caracteristicas import comisiones_habilitadas
from business_validation import money, text_value
from config import get_cdmx_now

comisiones_bp = Blueprint('comisiones', __name__, url_prefix='/api/comisiones')


def usuario_autorizado():
    user = db.session.get(User, get_jwt_identity())
    if not user or user.role not in ('admin', 'employee'):
        return None, (jsonify({'error': 'Acceso denegado'}), 403)
    if user.role != 'admin' and (not current_branch(user) or not comisiones_habilitadas()):
        return None, (jsonify({'error': 'Comisiones no está habilitado para empleados'}), 403)
    return user, None


@comisiones_bp.route('/pendientes', methods=['GET'])
@jwt_required()
def pendientes():
    user, error = usuario_autorizado()
    if error:
        return error
    try:
        dia = date.fromisoformat(request.args.get('fecha', get_cdmx_now().date().isoformat()))
        if dia < INICIO:
            raise ValueError('Solo se pueden registrar ventas desde el 18/11/2026')
        inicio, fin = rango(dia)
        query = DetalleVenta.query.join(Venta).filter(Venta.created_at >= inicio, Venta.created_at < fin)
        if user.role != 'admin':
            query = query.filter(Venta.sucursal_id == current_branch(user))
        elif request.args.get('sucursal_id'):
            query = query.filter(Venta.sucursal_id == request.args['sucursal_id'])
        unidades = []
        for detalle in query.order_by(Venta.created_at, DetalleVenta.id).all():
            if tipo_dispositivo(detalle.producto):
                unidades.extend(datos_unidad(detalle, u) for u in unidades_disponibles(detalle))
        response = jsonify(unidades=unidades, fecha_inicio=INICIO.isoformat())
        response.headers['Cache-Control'] = 'no-store'
        return response
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


def datos_registro(data, user):
    if 'empleado_comision_id' in data:
        e=db.session.get(EmpleadoComision,data.get('empleado_comision_id'))
        if not e or not e.activo or e.sucursal_id!=current_branch(user): raise ValueError('Selecciona un empleado activo de la sucursal.')
        empleado_id=e.id
        data={**data,'nombre_empleado':e.nombre};data.pop('empleado_comision_id')
    else:
        empleado_id=None
        if EmpleadoComision.query.filter_by(sucursal_id=current_branch(user),activo=True).first(): raise ValueError('Selecciona el empleado del catálogo.')
    if set(data) != {'detalle_venta_id', 'unidad', 'nombre_empleado'}:
        raise ValueError('Selecciona una unidad vendida e indica el nombre del empleado')
    unidad = data.get('unidad')
    if type(unidad) is not int or unidad < 1:
        raise ValueError('Selecciona una unidad válida')
    detalle = db.session.get(DetalleVenta, data.get('detalle_venta_id'))
    if not detalle:
        raise ValueError('Venta no disponible')
    # Serializa contra otras comisiones y contra las devoluciones de esta venta.
    venta = Venta.query.filter_by(id=detalle.venta_id, sucursal_id=current_branch(user)).with_for_update().first()
    if not venta or fecha_cdmx(venta.created_at).date() < INICIO:
        raise ValueError('Selecciona una venta de tu sucursal desde el 18/11/2026')
    # La venta pudo corregirse mientras esperábamos su bloqueo.
    db.session.refresh(detalle)
    db.session.expire(detalle, ['producto'])
    if not tipo_dispositivo(detalle.producto):
        raise ValueError('El producto no pertenece a Celulares o Tablets')
    if unidad not in unidades_disponibles(detalle):
        raise ValueError('Esta unidad ya tiene comisión o fue devuelta. Actualiza las ventas pendientes.')
    snapshot = datos_unidad(detalle, unidad)
    return dict(empleado_comision_id=empleado_id, detalle_venta_id=detalle.id, unidad=unidad, fecha_venta=venta.created_at,
                numero_venta=venta.numero_venta, producto_nombre=detalle.producto.nombre,
                dispositivo=snapshot['dispositivo'], costo=money(detalle.precio_unitario),
                metodo_pago=snapshot['metodo_pago'],
                nombre_empleado=text_value(data.get('nombre_empleado'), 'Usuario', 150, required=True))


@comisiones_bp.route('', methods=['GET', 'POST'])
@jwt_required()
def registros():
    user, error = usuario_autorizado()
    if error:
        return error
    if request.method == 'GET':
        try:
            query = Comision.query
            sucursal = request.args.get('sucursal_id')
            if user.role != 'admin':
                if sucursal and sucursal != current_branch(user):
                    return jsonify(error='Solo puedes consultar la sucursal activa.'), 403
                query = query.filter_by(sucursal_id=current_branch(user))
            elif sucursal:
                query = query.filter_by(sucursal_id=sucursal)
            empleado = request.args.get('empleado', '').strip()
            if empleado:
                query = query.filter(func.lower(Comision.nombre_empleado).contains(empleado.lower(), autoescape=True))
            estado = request.args.get('estado', 'todas')
            if estado not in ('todas', 'aprobadas', 'pendientes'): raise ValueError('Estado inválido')
            if estado != 'todas': query = query.filter(Comision.aprobada == (estado == 'aprobadas'))
            dispositivo = request.args.get('dispositivo', '')
            if dispositivo:
                if dispositivo not in ('Celular', 'Tablet'): raise ValueError('Dispositivo inválido')
                query = query.filter_by(dispositivo=dispositivo)
            tipo_fecha = request.args.get('tipo_fecha', 'registro')
            if tipo_fecha not in ('registro', 'venta'): raise ValueError('Tipo de fecha inválido')
            columna = Comision.created_at if tipo_fecha == 'registro' else Comision.fecha_venta
            desde = date.fromisoformat(request.args['desde']) if request.args.get('desde') else None
            hasta = date.fromisoformat(request.args['hasta']) if request.args.get('hasta') else None
            if desde and hasta and desde > hasta: raise ValueError('La fecha inicial debe ser anterior a la final')
            if desde: query = query.filter(columna >= rango(desde)[0])
            if hasta: query = query.filter(columna < rango(hasta)[1])
            pagina = int(request.args.get('pagina', 1)); por_pagina = int(request.args.get('por_pagina', 25))
            if pagina < 1 or por_pagina not in (10, 25, 50, 100): raise ValueError('Paginación inválida')
            total = query.count(); paginas = max(1, (total + por_pagina - 1) // por_pagina)
            pagina = min(pagina, paginas)
            aprobadas, monto = query.with_entities(
                func.sum(case((Comision.aprobada.is_(True), 1), else_=0)),
                func.sum(case((Comision.aprobada.is_(True), Comision.monto_comision), else_=0))).one()
            filas = query.order_by(Comision.created_at.desc(), Comision.id).offset((pagina-1)*por_pagina).limit(por_pagina).all()
            response = jsonify(comisiones=[c.to_dict() for c in filas], total=total, pagina=pagina,
                paginas=paginas, por_pagina=por_pagina, resumen=dict(aprobadas=aprobadas or 0,
                pendientes=total-(aprobadas or 0), monto_aprobado=float(monto or 0)))
            response.headers['Cache-Control'] = 'no-store'
            return response
        except (ValueError, OverflowError):
            return jsonify(error='Revisa las fechas, filtros y paginación.'), 400
    try:
        if user.role != 'employee':
            return jsonify({'error': 'La captura corresponde a empleados de sucursal'}), 403
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError('Registro inválido')
        registro = Comision(**datos_registro(data, user), sucursal_id=current_branch(user), creado_por_id=user.id, created_at=get_cdmx_now())
        db.session.add(registro)
        db.session.commit()
        return jsonify(registro.to_dict()), 201
    except ValueError as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify(error='La unidad ya fue asignada. Actualiza las ventas pendientes.'), 409


@comisiones_bp.route('/<registro_id>', methods=['PUT', 'DELETE'])
@jwt_required()
def modificar(registro_id):
    user, error = usuario_autorizado()
    if error:
        return error
    query = Comision.query.filter_by(id=registro_id)
    if user.role != 'admin' and not delegated_access():
        query = query.filter_by(sucursal_id=current_branch(user))
    registro = query.with_for_update().first()
    if not registro:
        return jsonify({'error': 'Registro no encontrado'}), 404
    if registro.pago_comision_id:
        return jsonify(error='Esta comisión ya fue pagada; su importe e historial se conservan.'),409
    if user.role == 'admin':
        if request.method == 'DELETE':
            return jsonify({'error': 'Admin puede modificar el importe y la aprobación'}), 403
        try:
            data = request.get_json(silent=True)
            if not isinstance(data, dict) or set(data) - {'monto_comision', 'aprobada', 'empleado_comision_id'} or not isinstance(data.get('aprobada'), bool):
                raise ValueError('Indica el monto y la aprobación de la comisión')
            if 'empleado_comision_id' in data:
                e=db.session.get(EmpleadoComision,data['empleado_comision_id'])
                if not e or e.sucursal_id!=registro.sucursal_id: raise ValueError('El empleado debe pertenecer a la sucursal del registro.')
                registro.empleado_comision_id=e.id;registro.nombre_empleado=e.nombre
            monto = money(data.get('monto_comision'), 'Comisión')
            registro.monto_comision = monto
            registro.aprobada = data['aprobada']
        except ValueError as exc:
            db.session.rollback()
            return jsonify({'error': str(exc)}), 400
    else:
        if registro.creado_por_id != user.id:
            return jsonify({'error': 'Solo puedes modificar los registros que capturaste'}), 403
        if registro.aprobada:
            return jsonify({'error': 'Una comisión aprobada no puede editarse ni eliminarse'}), 409
        if request.method == 'DELETE':
            db.session.delete(registro)
            db.session.commit()
            return jsonify({'message': 'Registro eliminado'})
        try:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                raise ValueError('Registro inválido')
            if set(data)=={'empleado_comision_id'}:
                e=db.session.get(EmpleadoComision,data['empleado_comision_id'])
                if not e or not e.activo or e.sucursal_id!=registro.sucursal_id: raise ValueError('Empleado inválido.')
                registro.empleado_comision_id=e.id;data={'nombre_empleado':e.nombre}
            elif registro.empleado_comision_id:
                raise ValueError('Selecciona el empleado del catálogo.')
            if set(data) != {'nombre_empleado'}:
                raise ValueError('Solo puedes corregir el nombre del empleado; la venta vinculada se conserva')
            registro.nombre_empleado = text_value(data.get('nombre_empleado'), 'Usuario', 150, required=True)
        except ValueError as exc:
            db.session.rollback()
            return jsonify({'error': str(exc)}), 400
    db.session.commit()
    return jsonify(registro.to_dict())


from permissions import authorize_request
comisiones_bp.before_request(authorize_request)
