"""Cortes semanales por empleado; pagos independientes de caja y ventas."""
import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Sucursal, Comision, EmpleadoComision, PagoComision
from permissions import authorize_request, current_branch, can
from config import get_cdmx_now
from comisiones_ventas import fecha_cdmx
from business_validation import text_value, money
from routes_caracteristicas import comisiones_habilitadas

semanales_bp=Blueprint('comisiones_semanales',__name__,url_prefix='/api/comisiones/semanales')
semanales_bp.before_request(authorize_request)


def usuario(admin=False):
    u=db.session.get(User,get_jwt_identity())
    if not u or (admin and u.role!='admin'): raise PermissionError('Solo admin puede realizar esta operación.')
    if u.role!='admin' and (not can(u,'comisiones','ver') or not comisiones_habilitadas()): raise PermissionError('No tienes acceso a comisiones.')
    return u


def empleados(u):
    q=EmpleadoComision.query
    if u.role!='admin': q=q.filter_by(sucursal_id=current_branch(u))
    elif request.args.get('sucursal_id'): q=q.filter_by(sucursal_id=request.args['sucursal_id'])
    return q


def empleado_dict(e): return dict(id=e.id,nombre=e.nombre,sucursal_id=e.sucursal_id,sucursal_nombre=e.sucursal.nombre,dia_pago=e.dia_pago,activo=e.activo)


@semanales_bp.errorhandler(ValueError)
def invalido(e):
    db.session.rollback();return jsonify(error=str(e)),400


@semanales_bp.errorhandler(PermissionError)
def prohibido(e):
    db.session.rollback();return jsonify(error=str(e)),403


@semanales_bp.route('/empleados',methods=['GET','POST'])
@jwt_required()
def catalogo():
    u=usuario(request.method=='POST')
    if request.method=='GET': return jsonify([empleado_dict(e) for e in empleados(u).order_by(EmpleadoComision.nombre).all()])
    return escribir(EmpleadoComision(),nuevo=True)


def escribir(e,nuevo=False):
    d=request.get_json(silent=True)
    if not isinstance(d,dict): raise ValueError('Solicitud inválida.')
    nombre=text_value(d.get('nombre'),'Nombre',150,True)
    dia=d.get('dia_pago')
    if type(dia) is not int or not 0<=dia<=6: raise ValueError('Selecciona el día de pago.')
    suc=db.session.get(Sucursal,d.get('sucursal_id'))
    if not suc: raise ValueError('Sucursal inválida.')
    if not nuevo and suc.id!=e.sucursal_id: raise ValueError('Crea otro empleado para cambiar de sucursal; se conserva el historial anterior.')
    if type(d.get('activo',True)) is not bool: raise ValueError('Estado inválido.')
    e.nombre=nombre;e.dia_pago=dia;e.sucursal_id=suc.id;e.activo=d.get('activo',True)
    db.session.add(e);db.session.commit();return jsonify(empleado_dict(e)),201 if nuevo else 200


@semanales_bp.put('/empleados/<id>')
@jwt_required()
def actualizar_empleado(id):
    usuario(True)
    e=EmpleadoComision.query.filter_by(id=id).with_for_update().first()
    if not e: raise ValueError('Empleado inexistente.')
    return escribir(e)


def corte(e,hoy):
    pago=hoy+timedelta(days=(e.dia_pago-hoy.weekday())%7)
    return pago-timedelta(days=6),pago,pago


def fecha_registro(c): return fecha_cdmx(c.fecha_venta or c.created_at).date()


def pendientes_pago(e,fin,lock=False):
    # Un corte pagado queda cerrado: las aprobaciones posteriores pasan al siguiente.
    if PagoComision.query.filter_by(empleado_id=e.id).filter(PagoComision.hasta>=fin).first():
        return []
    q=Comision.query.filter_by(empleado_comision_id=e.id,pago_comision_id=None,aprobada=True).order_by(Comision.id)
    if lock:q=q.with_for_update().populate_existing()
    return [c for c in q.all() if fecha_registro(c)<=fin]


def firma(e,fin,filas):
    return hashlib.sha256(json.dumps([e.id,e.dia_pago,fin.isoformat(),[(c.id,str(c.monto_comision),c.empleado_comision_id) for c in filas]],sort_keys=True).encode()).hexdigest()


def pago_dict(p):
    return dict(id=p.id,empleado_id=p.empleado_id,empleado=p.empleado_nombre,sucursal_id=p.sucursal_id,
        desde=p.desde.isoformat(),hasta=p.hasta.isoformat(),fecha_pago=fecha_cdmx(p.fecha_pago).isoformat(),
        monto=float(p.monto),comisiones=p.detalles,usuario=p.usuario_nombre)


@semanales_bp.get('')
@jwt_required()
def resumen():
    u=usuario();hoy=get_cdmx_now().date();salida=[]
    for e in empleados(u).order_by(EmpleadoComision.nombre).all():
        ini,fin,pago=corte(e,hoy)
        if PagoComision.query.filter_by(empleado_id=e.id).filter(PagoComision.hasta>=fin).first():
            ini+=timedelta(days=7);fin+=timedelta(days=7);pago+=timedelta(days=7)
        todas=Comision.query.filter_by(empleado_comision_id=e.id,pago_comision_id=None).all()
        semana=[c for c in todas if ini<=fecha_registro(c)<=fin]
        anteriores=[c for c in todas if fecha_registro(c)<ini]
        aprobadas_semana=[c for c in semana if c.aprobada]
        aprobadas_anteriores=[c for c in anteriores if c.aprobada]
        monto_semana=sum((c.monto_comision or Decimal(0) for c in aprobadas_semana),Decimal(0))
        monto_anterior=sum((c.monto_comision or Decimal(0) for c in aprobadas_anteriores),Decimal(0))
        fin_pagable=corte(e,hoy)[1]
        listas=pendientes_pago(e,fin_pagable)
        salida.append(dict(**empleado_dict(e),desde=ini.isoformat(),hasta=fin.isoformat(),dia_programado=pago.isoformat(),
            aprobado_semana=float(monto_semana),cantidad_aprobada_semana=len(aprobadas_semana),
            aprobado_anterior=float(monto_anterior),cantidad_aprobada_anterior=len(aprobadas_anteriores),
            total_proximo_pago=float(monto_semana+monto_anterior),
            detalle_aprobadas=[dict(id=c.id,producto=c.producto_nombre or c.dispositivo,
                fecha=fecha_registro(c).isoformat(),fecha_registro=c.fecha_venta is None,
                comision=float(c.monto_comision or Decimal(0)),anterior=fecha_registro(c)<ini)
                for c in sorted(aprobadas_anteriores+aprobadas_semana,key=lambda c:(fecha_registro(c),c.id))],
            anteriores_sin_aprobar=sum(not c.aprobada for c in anteriores),
            acumulado=float(sum((c.monto_comision or Decimal(0) for c in semana),Decimal(0))),
            sin_monto=sum(c.monto_comision is None for c in semana),pendientes_aprobacion=sum(not c.aprobada for c in todas),
            anteriores=len(anteriores),por_pagar=float(sum((c.monto_comision or Decimal(0) for c in listas),Decimal(0))),
            cantidad_pago=len(listas),hasta_pagable=fin_pagable.isoformat(),version=firma(e,fin_pagable,listas)))
    ids=[e['id'] for e in salida]
    q=PagoComision.query.filter(PagoComision.empleado_id.in_(ids))
    from comisiones_ventas import rango
    try:
        desde=date.fromisoformat(request.args['desde']) if request.args.get('desde') else None
        hasta=date.fromisoformat(request.args['hasta']) if request.args.get('hasta') else None
        if desde and hasta and desde>hasta: raise ValueError()
        if desde:q=q.filter(PagoComision.fecha_pago>=rango(desde)[0])
        if hasta:q=q.filter(PagoComision.fecha_pago<rango(hasta)[1])
        pagina=max(1,int(request.args.get('pagina',1)))
    except (ValueError,OverflowError): raise ValueError('Fechas o página inválidas.')
    total=q.count();paginas=max(1,(total+24)//25);pagina=min(pagina,paginas)
    monto=db.session.query(db.func.coalesce(db.func.sum(PagoComision.monto),0)).filter(PagoComision.id.in_(q.with_entities(PagoComision.id))).scalar()
    historico=q.order_by(PagoComision.fecha_pago.desc(),PagoComision.id).offset((pagina-1)*25).limit(25).all()
    sin_asignar=Comision.query.filter_by(empleado_comision_id=None)
    if u.role!='admin':sin_asignar=sin_asignar.filter_by(sucursal_id=current_branch(u))
    elif request.args.get('sucursal_id'):sin_asignar=sin_asignar.filter_by(sucursal_id=request.args['sucursal_id'])
    return jsonify(empleados=salida,pagos=[pago_dict(p) for p in historico],total_entregado=float(monto),total_pagos=total,pagina=pagina,paginas=paginas,sin_asignar=sin_asignar.count())


@semanales_bp.post('/empleados/<id>/pagar')
@jwt_required()
def pagar(id):
    u=usuario(True)
    e=EmpleadoComision.query.filter_by(id=id).with_for_update().first()
    if not e: raise ValueError('Empleado inexistente.')
    ini,fin,programado=corte(e,get_cdmx_now().date())
    filas=pendientes_pago(e,fin,True)
    d=request.get_json(silent=True)
    if not isinstance(d,dict): raise ValueError('Solicitud inválida.')
    if d.get('version')!=firma(e,fin,filas): return jsonify(error='Las comisiones cambiaron. Actualiza y revisa el importe antes de pagar.'),409
    if not filas: raise ValueError('No hay comisiones aprobadas por pagar.')
    if any(c.monto_comision is None for c in filas): raise ValueError('Hay comisiones sin monto.')
    p=PagoComision(empleado_id=e.id,sucursal_id=e.sucursal_id,empleado_nombre=e.nombre,usuario_id=u.id,usuario_nombre=u.username,
        fecha_pago=get_cdmx_now(),desde=min(ini,min(fecha_registro(c) for c in filas)),hasta=fin,monto=money(sum((c.monto_comision for c in filas),Decimal(0))),
        detalles=[dict(id=c.id,fecha_venta=fecha_registro(c).isoformat(),producto=c.producto_nombre or c.dispositivo,monto=str(c.monto_comision)) for c in filas])
    db.session.add(p);db.session.flush()
    for c in filas:c.pago_comision_id=p.id
    db.session.commit();return jsonify(pago_dict(p)),201
