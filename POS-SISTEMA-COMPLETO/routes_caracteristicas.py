"""Preferencias globales y competencia mensual sin exponer importes."""
from datetime import datetime
from decimal import Decimal
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from models import db, ConfiguracionSistema, Sucursal, Venta
from routes_admin import admin_required
from config import CDMX_TZ, get_cdmx_now

caracteristicas_bp = Blueprint('caracteristicas', __name__, url_prefix='/api/caracteristicas')
MODOS = ('productos', 'competencia', 'oculto')


def modo_panel():
    config = db.session.get(ConfiguracionSistema, 1)
    return config.panel_ventas if config else 'productos'


@caracteristicas_bp.route('', methods=['GET'])
@admin_required
def consultar():
    return jsonify({'panel_ventas': modo_panel(), 'comisiones_habilitadas': comisiones_habilitadas()})


@caracteristicas_bp.route('', methods=['PUT'])
@admin_required
def guardar():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get('panel_ventas') not in MODOS:
        return jsonify({'error': 'Selecciona productos, competencia u oculto'}), 400
    config = db.session.get(ConfiguracionSistema, 1)
    if not config:
        config = ConfiguracionSistema(id=1)
        db.session.add(config)
    if 'comisiones_habilitadas' in data and not isinstance(data['comisiones_habilitadas'], bool):
        return jsonify({'error': 'Comisiones debe ser verdadero o falso'}), 400
    config.panel_ventas = data['panel_ventas']
    if 'comisiones_habilitadas' in data:
        config.comisiones_habilitadas = data['comisiones_habilitadas']
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'No se pudo guardar la configuración. Intenta nuevamente.'}), 409
    return jsonify({'panel_ventas': config.panel_ventas, 'comisiones_habilitadas': config.comisiones_habilitadas})


@caracteristicas_bp.route('/panel-ventas', methods=['GET'])
@jwt_required()
def panel_ventas():
    mode = modo_panel()
    payload = {'modo': mode}
    if mode == 'competencia':
        now = get_cdmx_now()
        start = CDMX_TZ.localize(datetime(now.year, now.month, 1))
        end = CDMX_TZ.localize(datetime(now.year + (now.month == 12), now.month % 12 + 1, 1))
        totals = db.session.query(Venta.sucursal_id, func.sum(Venta.total)).filter(
            Venta.created_at >= start, Venta.created_at < end
        ).group_by(Venta.sucursal_id).all()
        amounts = {branch: max(Decimal('0'), total or Decimal('0')) for branch, total in totals}
        branches = Sucursal.query.filter_by(is_active=True).all()
        branches.sort(key=lambda b: (-amounts.get(b.id, Decimal('0')), b.nombre.casefold(), b.id))
        maximum = max((amounts.get(b.id, Decimal('0')) for b in branches), default=Decimal('0'))
        payload.update({
            'periodo': start.strftime('%Y-%m'),
            'hay_ventas': maximum > 0,
            # Solo proporciones visuales; nunca devolver importes, totales ni tickets.
            'sucursales': [{'id': b.id, 'nombre': b.nombre,
                           'barra': round(float(amounts.get(b.id, Decimal('0')) / maximum * 100), 2) if maximum else 0,
                           'lider': bool(maximum and amounts.get(b.id, Decimal('0')) == maximum)} for b in branches]
        })
    response = jsonify(payload)
    response.headers['Cache-Control'] = 'no-store'
    return response


def comisiones_habilitadas():
    config = db.session.get(ConfiguracionSistema, 1)
    return bool(config and config.comisiones_habilitadas)


@caracteristicas_bp.route('/acceso', methods=['GET'])
@jwt_required()
def acceso():
    response = jsonify({'comisiones_habilitadas': comisiones_habilitadas()})
    response.headers['Cache-Control'] = 'no-store'
    return response
