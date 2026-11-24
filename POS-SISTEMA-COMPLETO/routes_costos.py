"""Costos y utilidad privados de administradores. No delegables."""
from copy import deepcopy
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
import time
import uuid
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from models import (db, Producto, Categoria, Subcategoria, Sucursal, Venta, DetalleVenta,
                    DevolucionVenta, ReglaCosto, RevisionCosto)
from routes_admin import admin_required
from permissions import authorize_request
from business_validation import money, text_value
from config import CDMX_TZ, get_cdmx_now
from costos_servicio import identificar, validar_asociaciones
from reclasificacion_logs import registrar_error

costos_bp = Blueprint('costos', __name__, url_prefix='/api/costos')
costos_bp.before_request(authorize_request)


class Conflicto(ValueError): pass


@costos_bp.errorhandler(ValueError)
def invalid(error):
    db.session.rollback()
    return jsonify(error=str(error)), 409 if isinstance(error, Conflicto) else 400


@costos_bp.errorhandler(SQLAlchemyError)
def db_error(error):
    db.session.rollback()
    return jsonify(error='No se guardaron cambios. Actualiza la revisión y vuelve a intentar.'), 409


def datos():
    data = request.get_json(silent=True)
    if not isinstance(data,dict): raise ValueError('Solicitud inválida')
    return data


def monto(value): return str(value) if value is not None else None


def regla_dict(r):
    return dict(id=r.id,nombre=r.nombre,criterio=r.criterio,costo=monto(r.costo),activa=r.activa,version=r.version)


@costos_bp.get('/reglas')
@admin_required
def reglas():
    return jsonify([regla_dict(r) for r in ReglaCosto.query.order_by(ReglaCosto.nombre).all()])


@costos_bp.post('/reglas')
@admin_required
def crear_regla():
    r = ReglaCosto(); return escribir_regla(r, True)


@costos_bp.put('/reglas/<id>')
@admin_required
def editar_regla(id):
    r = ReglaCosto.query.filter_by(id=id).with_for_update().first()
    if not r: raise ValueError('Regla inexistente')
    if datos().get('version') != r.version: raise Conflicto('La regla cambió. Recarga antes de editar.')
    return escribir_regla(r)


def escribir_regla(r, nuevo=False):
    data = datos()
    r.nombre = text_value(data.get('nombre'), 'Nombre',120,True)
    r.criterio = text_value(data.get('criterio'), 'Criterio',1500,True)
    r.costo = money(data.get('costo'), 'Costo unitario')
    if type(data.get('activa')) is not bool: raise ValueError('Indica si la regla está activa')
    r.activa=data['activa'];r.version=1 if nuevo else r.version+1
    db.session.add(r);db.session.commit()
    return jsonify(regla_dict(r)), 201 if nuevo else 200


def mostrar(r, filas=True):
    return dict(id=r.id,fecha=r.created_at.isoformat(),version=r.version,total=len(r.filas),
        resumen=dict(Counter(f['estado'] for f in r.filas)),ocupado=r.bloqueado_hasta > time.time(),
        **({'filas':r.filas} if filas else {}))


def obtener(id, edicion=False):
    r=RevisionCosto.query.filter_by(id=id).with_for_update().first()
    if not r: raise ValueError('Revisión inexistente')
    if edicion:
        if r.bloqueado_hasta > time.time(): raise Conflicto('Espera a que termine el lote en proceso.')
        if datos().get('version') != r.version: raise Conflicto('La revisión cambió en otra sesión. Actualiza.')
    return r


def guardar(r, filas):
    r.filas=filas;r.version+=1;db.session.commit()
    return jsonify(mostrar(r))


@costos_bp.get('/revisiones')
@admin_required
def revisiones():
    return jsonify([mostrar(r,False) for r in RevisionCosto.query.order_by(RevisionCosto.created_at.desc()).all()])


@costos_bp.post('/revisiones')
@admin_required
def crear_revision():
    filas=[]
    for p in Producto.query.order_by(Producto.codigo).all():
        s=p.subcategoria
        filas.append(dict(id=p.id,codigo=p.codigo,nombre=p.nombre,subcategoria_id=p.subcategoria_id,
            categoria=s.categoria.nombre,subcategoria=s.nombre,costo_actual=monto(p.costo_compra),costo_propuesto=None,
            regla=None,estado='conservado' if p.costo_compra is not None else 'sin_revisar',motivo='',editada=False))
    r=RevisionCosto(creado_por_id=get_jwt_identity(),filas=filas)
    db.session.add(r);db.session.commit()
    return jsonify(mostrar(r)),201


@costos_bp.get('/revisiones/<id>')
@admin_required
def detalle(id): return jsonify(mostrar(obtener(id)))


@costos_bp.post('/revisiones/<id>/procesar')
@admin_required
def procesar(id):
    r=obtener(id)
    if r.bloqueado_hasta > time.time(): raise Conflicto('Hay un lote en proceso.')
    filas_lote=[f for f in r.filas if f['estado']=='sin_revisar'][:10]
    if not filas_lote: return jsonify(mostrar(r))
    rules=[regla_dict(rule) for rule in ReglaCosto.query.filter_by(activa=True).all()]
    if not rules: raise ValueError('Agrega una regla activa o captura los costos manualmente.')
    token=str(uuid.uuid4());r.token_lote=token;r.bloqueado_hasta=time.time()+90
    entrada=[{k:f[k] for k in ('codigo','nombre','categoria','subcategoria')} for f in filas_lote]
    db.session.commit()
    try:
        respuestas=validar_asociaciones(identificar(entrada,rules,id,token),entrada,rules)
    except Exception as error:
        registrar_error(error,etapa='procesar_costos',revision=id,lote=token,productos=entrada)
        r=obtener(id)
        if r.token_lote==token:
            r.token_lote=None;r.bloqueado_hasta=0;db.session.commit()
        raise ValueError('No se pudo revisar el lote. El avance está guardado; reintenta o edita los costos manualmente.')
    r=obtener(id)
    if r.token_lote != token: raise Conflicto('El lote fue retomado en otra sesión. Actualiza.')
    filas=deepcopy(r.filas);por_codigo={f['codigo']:f for f in respuestas};por_regla={r['id']:r for r in rules}
    for f in filas:
        if f['codigo'] not in por_codigo: continue
        respuesta=por_codigo[f['codigo']];f['motivo']=respuesta['motivo'][:1000]
        if respuesta['ambiguo']:
            f['estado']='pendiente';continue
        rule=por_regla[respuesta['regla_id']]
        f.update(estado='listo',regla=rule,costo_propuesto=rule['costo'])
    r.token_lote=None;r.bloqueado_hasta=0
    return guardar(r,filas)


@costos_bp.post('/revisiones/<id>/editar')
@admin_required
def editar(id):
    r=obtener(id,True);data=datos();filas=deepcopy(r.filas)
    f=next((f for f in filas if f['id']==data.get('producto_id')),None)
    if not f or f['estado']=='aplicado': raise ValueError('Selecciona una fila no aplicada')
    costo=money(data.get('costo'), 'Costo unitario')
    motivo=text_value(data.get('motivo'), 'Motivo',500,True)
    f.update(costo_propuesto=str(costo),regla=None,editada=True,motivo=motivo,
        estado='conservado' if f['costo_actual'] is not None and costo==Decimal(f['costo_actual']) else 'listo')
    return guardar(r,filas)


@costos_bp.post('/revisiones/<id>/aplicar')
@admin_required
def aplicar(id):
    r=obtener(id,True);filas=deepcopy(r.filas)
    elegidas=sorted((f for f in filas if f['estado']=='listo'),key=lambda f:f['id'])
    # Bloquear reglas en orden fijo para que no cambien durante la aplicación.
    rules={}
    for rid in sorted({f['regla']['id'] for f in elegidas if f['regla']}):
        rules[rid]=ReglaCosto.query.filter_by(id=rid).with_for_update().first()
    for f in elegidas:
        p=Producto.query.filter_by(id=f['id']).with_for_update().first()
        if not p or p.nombre!=f['nombre'] or p.subcategoria_id!=f['subcategoria_id'] or monto(p.costo_compra)!=f['costo_actual']:
            raise Conflicto(f"{f['codigo']}: el producto cambió. Inicia una nueva revisión; no se aplicó ningún cambio.")
        if p.subcategoria.nombre!=f['subcategoria'] or p.subcategoria.categoria.nombre!=f['categoria']:
            raise Conflicto('La clasificación cambió. Inicia una nueva revisión.')
        if f['regla']:
            rule=rules[f['regla']['id']]
            if not rule or not rule.activa or regla_dict(rule)!=f['regla']:
                raise Conflicto('Una regla cambió. Inicia una nueva revisión o confirma manualmente el costo.')
            costo=rule.costo
        else: costo=money(f['costo_propuesto'])
        p.costo_compra=costo
        f.update(estado='aplicado',aplicado_por=get_jwt_identity(),aplicado_en=get_cdmx_now().isoformat())
    return guardar(r,filas)


@costos_bp.get('/utilidad')
@admin_required
def utilidad():
    try:
        desde=datetime.strptime(request.args.get('fecha_inicio',''),'%Y-%m-%d').date()
        hasta=datetime.strptime(request.args.get('fecha_fin',''),'%Y-%m-%d').date()
        if desde>hasta: raise ValueError()
        inicio=CDMX_TZ.localize(datetime.combine(desde,datetime.min.time()))
        fin=CDMX_TZ.localize(datetime.combine(hasta+timedelta(days=1),datetime.min.time()))
    except (ValueError,OverflowError): raise ValueError('Selecciona fechas válidas')
    agrupacion=request.args.get('agrupar','producto')
    if agrupacion not in ('producto','categoria','sucursal'): raise ValueError('Agrupación inválida')
    # Agregar devoluciones antes del join evita multiplicar detalle/costo por devolución.
    returns=db.session.query(DevolucionVenta.detalle_venta_id.label('detalle'),func.sum(DevolucionVenta.cantidad_devuelta).label('cantidad')).group_by(DevolucionVenta.detalle_venta_id).subquery()
    query=db.session.query(DetalleVenta,Producto,Categoria,Sucursal,returns.c.cantidad).join(Venta,Venta.id==DetalleVenta.venta_id).join(
        Producto,Producto.id==DetalleVenta.producto_id).join(Subcategoria,Subcategoria.id==Producto.subcategoria_id).join(
        Categoria,Categoria.id==Subcategoria.categoria_id).join(Sucursal,Sucursal.id==Venta.sucursal_id).outerjoin(returns,returns.c.detalle==DetalleVenta.id).filter(Venta.created_at>=inicio,Venta.created_at<fin)
    if request.args.get('sucursal_id'): query=query.filter(Venta.sucursal_id==request.args['sucursal_id'])
    def vacio(): return dict(unidades=0,ventas=Decimal('0'),ventas_con_costo=Decimal('0'),costo=Decimal('0'),unidades_sin_costo=0,unidades_estimadas=0,unidades_costo_guardado=0)
    groups={};total=vacio()
    for d,p,cat,suc,devueltas in query.all():
        units=max(0,d.cantidad-(devueltas or 0))
        if not units: continue
        entity={'producto':p,'categoria':cat,'sucursal':suc}[agrupacion]
        key=entity.id
        if key not in groups: groups[key]=dict(id=key,nombre=entity.nombre,**({'codigo':p.codigo} if agrupacion=='producto' else {}),**vacio())
        snapshot=d.costo_compra_unitario
        cost=snapshot if snapshot is not None else p.costo_compra
        revenue=d.precio_unitario*units
        for item in (groups[key],total):
            item['unidades']+=units;item['ventas']+=revenue
            if cost is None: item['unidades_sin_costo']+=units
            else:
                item['ventas_con_costo']+=revenue;item['costo']+=cost*units
                item['unidades_estimadas' if snapshot is None else 'unidades_costo_guardado']+=units
    def serializar(item):
        profit=item['ventas_con_costo']-item['costo']
        return {**{k:float(v.quantize(Decimal('.01'))) if isinstance(v,Decimal) else v for k,v in item.items()},
            'utilidad_con_costo':float(profit.quantize(Decimal('.01'))),
            'utilidad':None if item['unidades_sin_costo'] else float(profit.quantize(Decimal('.01'))),
            'margen':float((profit/item['ventas_con_costo']*100).quantize(Decimal('.01'))) if item['ventas_con_costo'] else None}
    return jsonify(fecha_inicio=desde.isoformat(),fecha_fin=hasta.isoformat(),agrupar=agrupacion,
        resumen=serializar(total),filas=[serializar(v) for v in sorted(groups.values(),key=lambda v:(-v['ventas'],v['nombre'],v['id']))])
