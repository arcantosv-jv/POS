"""Correcciones auditadas de ventas aún no incluidas en un cierre."""
import hashlib
import json
from decimal import Decimal
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Venta, Producto, Stock, Comision
from permissions import can, allowed_branches
from config import get_cdmx_now, CDMX_TZ
from cash_accounting import lock_branch, set_net_payments, METHODS
from business_validation import money, text_value

edicion_ventas_bp = Blueprint('edicion_ventas', __name__, url_prefix='/api/ventas')


def bloqueo(v):
    fecha=v.created_at
    if fecha.tzinfo is None: fecha=CDMX_TZ.localize(fecha)
    if fecha.astimezone(CDMX_TZ).date()!=get_cdmx_now().date(): return 'Solo se pueden corregir ventas del día actual.'
    if v.cierre_caja_id: return 'Esta venta ya está incluida en un cierre de caja.'
    if v.numero_venta.startswith('AP-'): return 'Esta venta proviene de un apartado entregado.'
    if v.devoluciones: return 'Esta venta tiene devoluciones.'
    if Comision.query.filter(Comision.detalle_venta_id.in_([d.id for d in v.detalles])).first(): return 'Esta venta tiene comisiones asignadas.'
    return None


def estado(v):
    return dict(total=str(v.total), forma_pago=v.forma_pago,
        detalles=[dict(id=d.id,producto_id=d.producto_id,producto_nombre=d.producto.nombre,
                       cantidad=d.cantidad,precio_unitario=str(d.precio_unitario),sin_stock=d.sin_stock) for d in sorted(v.detalles,key=lambda d:d.id)],
        pagos=[dict(metodo_pago=p.metodo_pago,monto=str(p.monto)) for p in sorted(v.pagos,key=lambda p:p.metodo_pago)] or [dict(metodo_pago=v.forma_pago,monto=str(v.total))])


def version(v):
    return hashlib.sha256(json.dumps([estado(v),v.ediciones or []],sort_keys=True).encode()).hexdigest()


def autorizar():
    u=db.session.get(User,get_jwt_identity())
    if not u or not u.is_active or not can(u,'ventas-del-dia','editar'): raise PermissionError('No tienes permiso para editar ventas.')
    return u


def venta_autorizada(id,u):
    v=db.session.get(Venta,id)
    if not v: raise ValueError('Venta no encontrada.')
    if u.role!='admin' and v.sucursal_id not in allowed_branches(u): raise PermissionError('Acceso denegado a esta sucursal.')
    return v


@edicion_ventas_bp.errorhandler(ValueError)
def invalido(e):
    db.session.rollback()
    return jsonify(error=str(e)),400


@edicion_ventas_bp.errorhandler(PermissionError)
def denegado(e):
    db.session.rollback()
    return jsonify(error=str(e)),403


@edicion_ventas_bp.route('/<id>/edicion',methods=['GET','PUT'])
@jwt_required()
def editar(id):
    u=autorizar();v=venta_autorizada(id,u)
    if request.method=='GET':
        return jsonify(venta=estado(v),version=version(v),bloqueo=bloqueo(v),historial=v.ediciones or [])
    # Mismo orden de bloqueo que devoluciones; la sucursal serializa contra cierres.
    User.query.filter_by(id=v.cajero_id).with_for_update().first()
    lock_branch(v.sucursal_id)
    v=Venta.query.filter_by(id=id).populate_existing().with_for_update().one()
    db.session.expire(v,['detalles','pagos','devoluciones'])
    razon=bloqueo(v)
    if razon: return jsonify(error=razon),409
    data=request.get_json(silent=True)
    if not isinstance(data,dict): raise ValueError('Solicitud inválida.')
    if data.get('version')!=version(v): return jsonify(error='La venta cambió. Cierra el modal y vuelve a abrirlo.'),409
    motivo=text_value(data.get('motivo'),'Motivo',500,True)
    filas=data.get('detalles');pagos=data.get('pagos')
    actuales={d.id:d for d in v.detalles}
    if not isinstance(filas,list) or len(filas)!=len(actuales) or {f.get('id') for f in filas if isinstance(f,dict)}!=set(actuales):
        raise ValueError('Debes conservar los renglones de la venta y corregir su producto, cantidad o precio.')
    preparados=[];total=Decimal('0');impuestos=Decimal('0')
    for f in filas:
        qty=f.get('cantidad')
        if type(qty) is not int or not 1<=qty<=1000000: raise ValueError('Cantidad inválida: debe ser un entero positivo.')
        precio=money(f.get('precio_unitario'),'Precio de venta')
        p=db.session.get(Producto,f.get('producto_id'))
        if not p or (not p.is_active and p.id!=actuales[f['id']].producto_id): raise ValueError('Selecciona un producto activo.')
        total+=precio*qty
        impuesto=(precio*Decimal(str(p.impuesto))/100).quantize(Decimal('.01'))
        impuestos+=impuesto*qty
        preparados.append((actuales[f['id']],p,qty,precio,impuesto))
    money(total,'Total');money(impuestos,'Impuestos')
    if not isinstance(pagos,list) or not pagos: raise ValueError('Indica los pagos de la venta.')
    montos={m:Decimal('0') for m in METHODS}
    for pago in pagos:
        if not isinstance(pago,dict) or pago.get('metodo_pago') not in METHODS: raise ValueError('Método de pago inválido.')
        montos[pago['metodo_pago']]+=money(pago.get('monto'),'Pago')
    if sum(montos.values())!=total: raise ValueError('Los pagos deben coincidir con el nuevo total.')
    antes=estado(v)
    # Revertir solo unidades que realmente se descontaron. No tocar renglones sin cambio de inventario.
    afectados=[(d,p,q,precio,imp) for d,p,q,precio,imp in preparados if d.producto_id!=p.id or d.cantidad!=q]
    ids=sorted({pid for d,p,*_ in afectados for pid in (d.producto_id,p.id)})
    stocks={pid:Stock.query.filter_by(sucursal_id=v.sucursal_id,producto_id=pid).with_for_update().first() for pid in ids}
    for d,p,q,precio,imp in afectados:
        if not d.sin_stock:
            st=stocks[d.producto_id]
            if st is None:
                st=Stock(sucursal_id=v.sucursal_id,producto_id=d.producto_id,cantidad=0);db.session.add(st);stocks[d.producto_id]=st
            st.cantidad+=d.cantidad
    for d,p,q,precio,imp in afectados:
        st=stocks[p.id]
        d.sin_stock=not(st and st.cantidad>=q)
        if not d.sin_stock: st.cantidad-=q
    for d,p,q,precio,imp in preparados:
        if d.producto_id!=p.id: d.costo_compra_unitario=p.costo_compra
        d.producto_id=p.id;d.producto=p;d.cantidad=q;d.precio_unitario=precio;d.subtotal=precio*q;d.impuesto_unitario=imp
    v.total=total;v.total_impuestos=impuestos
    metodos=[m for m in METHODS if montos[m]>0]
    v.forma_pago=metodos[0] if len(metodos)==1 else ('mixto' if metodos else pagos[0]['metodo_pago'])
    set_net_payments(v,montos)
    v.ediciones=[*(v.ediciones or []),dict(fecha=get_cdmx_now().isoformat(),usuario_id=u.id,usuario=u.username,motivo=motivo,antes=antes,despues=estado(v))]
    db.session.commit()
    return jsonify(message='Venta corregida. Inventario y pagos actualizados.',version=version(v))


@edicion_ventas_bp.get('/edicion/productos')
@jwt_required()
def productos():
    autorizar()
    return jsonify([dict(id=p.id,nombre=p.nombre,codigo=p.codigo) for p in Producto.query.filter_by(is_active=True).order_by(Producto.nombre).all()])
