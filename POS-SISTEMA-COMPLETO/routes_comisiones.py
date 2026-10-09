"""Registro independiente de comisiones; sin movimientos de ventas o caja."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Comision
from routes_caracteristicas import comisiones_habilitadas
from business_validation import money, text_value
from config import get_cdmx_now

comisiones_bp = Blueprint('comisiones', __name__, url_prefix='/api/comisiones')


def usuario_autorizado():
    user = db.session.get(User, get_jwt_identity())
    if not user or user.role not in ('admin', 'employee'):
        return None, (jsonify({'error': 'Acceso denegado'}), 403)
    if user.role != 'admin' and (not user.sucursal_id or not comisiones_habilitadas()):
        return None, (jsonify({'error': 'Comisiones no está habilitado para empleados'}), 403)
    return user, None


def datos_registro(data):
    if set(data) - {'dispositivo', 'costo', 'metodo_pago', 'nombre_empleado'}:
        raise ValueError('Solo puedes modificar los datos del registro; la aprobación y comisión son exclusivas de admin')
    if data.get('dispositivo') not in ('Celular', 'Tablet'):
        raise ValueError('Selecciona Celular o Tablet')
    if data.get('metodo_pago') not in ('efectivo', 'tarjeta', 'transferencia'):
        raise ValueError('Selecciona un método de pago válido')
    return dict(dispositivo=data['dispositivo'], costo=money(data.get('costo'), 'Costo'),
                metodo_pago=data['metodo_pago'], nombre_empleado=text_value(data.get('nombre_empleado'), 'Usuario', 150, required=True))


@comisiones_bp.route('', methods=['GET', 'POST'])
@jwt_required()
def registros():
    user, error = usuario_autorizado()
    if error:
        return error
    if request.method == 'GET':
        query = Comision.query
        if user.role != 'admin':
            query = query.filter_by(sucursal_id=user.sucursal_id)
        response = jsonify({'comisiones': [c.to_dict() for c in query.order_by(Comision.created_at.desc(), Comision.id).all()]})
        response.headers['Cache-Control'] = 'no-store'
        return response
    try:
        if user.role != 'employee':
            return jsonify({'error': 'La captura corresponde a empleados de sucursal'}), 403
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError('Registro inválido')
        registro = Comision(**datos_registro(data), sucursal_id=user.sucursal_id, creado_por_id=user.id, created_at=get_cdmx_now())
        db.session.add(registro)
        db.session.commit()
        return jsonify(registro.to_dict()), 201
    except ValueError as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 400


@comisiones_bp.route('/<registro_id>', methods=['PUT', 'DELETE'])
@jwt_required()
def modificar(registro_id):
    user, error = usuario_autorizado()
    if error:
        return error
    query = Comision.query.filter_by(id=registro_id)
    if user.role != 'admin':
        query = query.filter_by(sucursal_id=user.sucursal_id)
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
            for key, value in datos_registro(data).items():
                setattr(registro, key, value)
        except ValueError as exc:
            db.session.rollback()
            return jsonify({'error': str(exc)}), 400
    db.session.commit()
    return jsonify(registro.to_dict())
