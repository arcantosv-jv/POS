"""Reservas y pagos independientes de Venta, PagoVenta y CierreCaja."""
import re
from apartado_venta import registrar_venta_entrega
from cash_accounting import lock_branch
from datetime import timedelta
from decimal import Decimal
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from models import db, User, Producto, Stock, Apartado, Sucursal, ConfiguracionSistema
from permissions import authorize_request, can
from business_validation import money, text_value
from config import get_cdmx_now

apartados_bp = Blueprint('apartados', __name__, url_prefix='/api/apartados')
apartados_bp.before_request(authorize_request)


def contexto(accion):
    user = db.session.get(User, get_jwt_identity())
    config = db.session.get(ConfiguracionSistema, 1)
    if user.role != 'admin' and (not config or not config.apartados_habilitados or not can(user, 'apartados', accion)):
        raise PermissionError('No tienes acceso a esta acción de Apartados')
    return user


def pagos(datos, monto):
    resultado = []
    if not isinstance(datos, list):
        raise ValueError('Indica el desglose del pago')
    for pago in datos:
        if not isinstance(pago, dict) or pago.get('metodo') not in ('efectivo', 'tarjeta', 'transferencia'):
            raise ValueError('Método de pago inválido')
        valor = money(pago.get('monto'))
        if valor > 0:
            resultado.append(dict(metodo=pago['metodo'], monto=str(valor)))
    if sum((Decimal(p['monto']) for p in resultado), Decimal(0)) != monto:
        raise ValueError('El desglose de pagos debe coincidir con el importe')
    return resultado


def evento(user, tipo, empleado, **datos):
    return dict(tipo=tipo, fecha=get_cdmx_now().isoformat(), usuario_id=user.id,
                empleado=text_value(empleado, 'Empleado', 150, required=True), **datos)


def presentar(registro, user):
    data = registro.to_dict()
    if user.role == 'admin':
        data['sin_existencias'] = any(p.get('faltantes', 0) > 0 for p in registro.productos)
    else:
        data['productos'] = [{k: v for k, v in p.items() if k not in ('reservados', 'faltantes')}
                             for p in registro.productos]
    return data


def bloquear_stock(branch, ids):
    # Orden estable para que operaciones concurrentes no reserven las mismas unidades.
    return {s.producto_id: s for s in Stock.query.filter(Stock.sucursal_id == branch, Stock.producto_id.in_(ids)).order_by(Stock.producto_id).with_for_update().all()}


@apartados_bp.route('', methods=['GET', 'POST'])
def registros():
    try:
        user = contexto('ver' if request.method == 'GET' else 'crear')
        if request.method == 'GET':
            query = Apartado.query
            branch = request.args.get('sucursal_id') if user.role == 'admin' else user.sucursal_id
            if branch:
                query = query.filter_by(sucursal_id=branch)
            return jsonify(apartados=[presentar(r, user) for r in query.order_by(Apartado.fecha.desc(), Apartado.id).all()])
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError('Datos inválidos')
        telefono = data.get('telefono')
        if not isinstance(telefono, str) or not re.fullmatch(r'[0-9]{10}', telefono):
            raise ValueError('El teléfono debe contener exactamente 10 dígitos numéricos')
        branch = data.get('sucursal_id') if user.role == 'admin' else user.sucursal_id
        if user.role != 'admin' and data.get('sucursal_id', branch) != branch:
            raise PermissionError('Solo puedes apartar en tu sucursal')
        if not branch or not Sucursal.query.filter_by(id=branch, is_active=True).first():
            raise ValueError('Selecciona una sucursal activa')
        plazo = data.get('plazo')
        if plazo not in (15, 30, 45):
            raise ValueError('Selecciona 15, 30 o 45 días')
        lineas = data.get('productos')
        if not isinstance(lineas, list) or not lineas or len(lineas) > 100:
            raise ValueError('Agrega entre 1 y 100 productos')
        ids = [p.get('producto_id') for p in lineas if isinstance(p, dict)]
        if len(ids) != len(lineas) or any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
            raise ValueError('Productos inválidos o repetidos; ajusta la cantidad')
        stocks = bloquear_stock(branch, ids)
        productos, total = [], Decimal(0)
        for linea in lineas:
            p = db.session.get(Producto, linea['producto_id'])
            cantidad = linea.get('cantidad')
            if not p or not p.is_active or type(cantidad) is not int or cantidad <= 0:
                raise ValueError('Producto o cantidad inválidos')
            stock = stocks.get(p.id)
            reservados = min(cantidad, max(0, stock.cantidad)) if stock else 0
            precio = money(linea.get('precio'), 'Precio')
            total += precio * cantidad
            productos.append(dict(producto_id=p.id, codigo=p.codigo, nombre=p.nombre, cantidad=cantidad, precio=str(precio), reservados=reservados, faltantes=cantidad-reservados))
            if stock:
                stock.cantidad -= reservados
                stock.reservado += reservados
        total = money(total, 'Total')
        anticipo = money(data.get('anticipo', 0), 'Anticipo')
        if anticipo > total:
            raise ValueError('El anticipo supera el total')
        r = Apartado(sucursal_id=branch, creado_por_id=user.id,
            cliente=text_value(data.get('cliente'), 'Cliente', 150, True),
            telefono=telefono,
            empleado=text_value(data.get('empleado'), 'Empleado', 150, True),
            observaciones=text_value(data.get('observaciones', ''), 'Observaciones'),
            plazo=plazo, fecha=get_cdmx_now().date(), vence=get_cdmx_now().date()+timedelta(days=plazo),
            estado='liquidado' if anticipo == total else 'pendiente', total=total, abonado=anticipo, productos=productos,
            movimientos=[evento(user, 'creacion', data.get('empleado'), monto=str(anticipo), pagos=pagos(data.get('pagos', []), anticipo))])
        db.session.add(r); db.session.commit()
        return jsonify(presentar(r, user)), 201
    except PermissionError as exc:
        db.session.rollback(); return jsonify(error=str(exc)), 403
    except ValueError as exc:
        db.session.rollback(); return jsonify(error=str(exc)), 400


@apartados_bp.route('/<apartado_id>/<accion>', methods=['POST'])
def operar(apartado_id, accion):
    try:
        if accion not in ('abonar', 'entregar', 'cancelar'):
            raise ValueError('Acción inválida')
        user = contexto(accion)
        if accion == 'cancelar' and user.role != 'admin':
            raise PermissionError('Solo admin puede cancelar y registrar devoluciones')
        r = Apartado.query.filter_by(id=apartado_id).with_for_update().first()
        if not r or (user.role != 'admin' and r.sucursal_id != user.sucursal_id):
            return jsonify(error='Apartado no encontrado'), 404
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError('Datos inválidos')
        if r.estado in ('entregado', 'cancelado'):
            raise ValueError('El apartado ya está cerrado')
        e = evento(user, accion, data.get('empleado'))
        if accion == 'abonar':
            monto = money(data.get('monto'))
            if monto <= 0 or monto > r.total-r.abonado:
                raise ValueError('El abono debe ser mayor a cero y no superar el saldo')
            e.update(monto=str(monto), pagos=pagos(data.get('pagos', []), monto))
            r.abonado += monto
            if r.abonado == r.total:
                r.estado = 'liquidado'
        else:
            if accion == 'entregar' and r.abonado != r.total:
                raise ValueError('Liquida el saldo antes de entregar')
            if accion == 'entregar':
                lock_branch(r.sucursal_id)
            stocks = bloquear_stock(r.sucursal_id, [p['producto_id'] for p in r.productos])
            for p in r.productos:
                stock = stocks.get(p['producto_id'])
                reservados = p.get('reservados', p['cantidad'])
                faltantes = p['cantidad'] - reservados
                if reservados and (not stock or stock.reservado < reservados):
                    raise ValueError('El apartado requiere revisión de admin antes de continuar')
                if stock:
                    stock.reservado -= reservados
                    if accion == 'cancelar':
                        stock.cantidad += reservados
                    else:
                        stock.cantidad -= min(faltantes, max(0, stock.cantidad))
            if accion == 'cancelar':
                monto = money(data.get('devolucion', 0), 'Devolución')
                if monto > r.abonado:
                    raise ValueError('No puedes devolver más de lo abonado')
                e.update(monto=str(monto), pagos=pagos(data.get('pagos', []), monto),
                         motivo=text_value(data.get('motivo'), 'Motivo', 2000, True))
            if accion == 'entregar':
                venta = registrar_venta_entrega(r, user.id)
                e.update(venta_id=venta.id, numero_venta=venta.numero_venta)
            r.estado = 'entregado' if accion == 'entregar' else 'cancelado'
        r.movimientos = r.movimientos + [e]
        db.session.commit()
        return jsonify(presentar(r, user))
    except PermissionError as exc:
        db.session.rollback(); return jsonify(error=str(exc)), 403
    except ValueError as exc:
        db.session.rollback(); return jsonify(error=str(exc)), 400
