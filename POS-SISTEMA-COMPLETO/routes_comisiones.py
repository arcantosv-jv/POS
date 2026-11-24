from permissions import delegated_access, current_branch, can
"""Registro independiente de comisiones; sin movimientos de ventas o caja."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Comision, Venta, DetalleVenta
from datetime import date
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
    return dict(detalle_venta_id=detalle.id, unidad=unidad, fecha_venta=venta.created_at,
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
        query = Comision.query
        if user.role != 'admin' and not delegated_access():
            query = query.filter_by(sucursal_id=current_branch(user))
        response = jsonify({'comisiones': [c.to_dict() for c in query.order_by(Comision.created_at.desc(), Comision.id).all()]})
        response.headers['Cache-Control'] = 'no-store'
        return response
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
    if user.role == 'admin':
        if request.method == 'DELETE':
            return jsonify({'error': 'Admin puede modificar el importe y la aprobación'}), 403
        try:
            data = request.get_json(silent=True)
            if not isinstance(data, dict) or set(data) - {'monto_comision', 'aprobada'} or not isinstance(data.get('aprobada'), bool):
                raise ValueError('Indica el monto y la aprobación de la comisión')
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
