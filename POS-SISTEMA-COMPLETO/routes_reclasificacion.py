"""Reclasificación global exclusiva de administradores, con revisión persistente."""
from copy import deepcopy
import time
import uuid
from collections import Counter
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from models import db, Producto, Categoria, Subcategoria, RevisionClasificacion
from routes_admin import admin_required
from clasificacion_productos import normalizar
from clasificacion_gemini import consultar, validar
from config import get_cdmx_now

reclasificacion_bp = Blueprint('reclasificacion', __name__, url_prefix='/api/reclasificacion')


class Conflicto(ValueError):
    pass


@reclasificacion_bp.errorhandler(ValueError)
def error_validacion(error):
    db.session.rollback()
    return jsonify(error=str(error)), 409 if isinstance(error, Conflicto) else 400


@reclasificacion_bp.errorhandler(SQLAlchemyError)
def error_base(error):
    db.session.rollback()
    return jsonify(error='No se guardaron cambios. Recarga la revisión e intenta nuevamente.'), 409


def datos():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError('Solicitud inválida')
    return data


def obtener(id, editar=False):
    r = RevisionClasificacion.query.filter_by(id=id).with_for_update().first()
    if not r:
        raise ValueError('Revisión inexistente')
    if editar:
        if r.bloqueado_hasta > time.time():
            raise Conflicto('Hay un lote en proceso. Espera a que termine.')
        if datos().get('version') != r.version:
            raise Conflicto('La revisión cambió en otra sesión. Recarga antes de guardar.')
    return r


def presentar(r, completo=True):
    conteo = dict(Counter(f['estado'] for f in r.filas))
    return {'id': r.id, 'fecha': r.created_at.isoformat(), 'version': r.version,
            'total': len(r.filas), 'resumen': conteo,
            'procesados': len(r.filas) - conteo.get('sin_revisar', 0),
            'ocupado': r.bloqueado_hasta > time.time(),
            **({'filas': r.filas} if completo else {})}


def guardar(r, filas):
    r.filas = filas
    r.version += 1
    db.session.commit()
    return jsonify(presentar(r))


def nombre(value):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 100:
        raise ValueError('Escribe nombres de categoría y subcategoría de 1 a 100 caracteres')
    return value.strip()


def resolver(cat, sub, crear=False):
    cat, sub = nombre(cat), nombre(sub)
    cats = [c for c in Categoria.query.all() if normalizar(c.nombre) == normalizar(cat)]
    if len(cats) > 1 or (cats and not cats[0].is_active):
        raise ValueError(f'Categoría duplicada o inactiva: {cat}')
    c = cats[0] if cats else None
    opciones = [] if c is None else [s for s in Subcategoria.query.filter_by(categoria_id=c.id).all()
                                    if normalizar(s.nombre) == normalizar(sub)]
    if len(opciones) > 1 or (opciones and not opciones[0].is_active):
        raise ValueError(f'Subcategoría duplicada o inactiva: {sub}')
    if opciones:
        return opciones[0], c.nombre, opciones[0].nombre
    if crear:
        if c is None:
            c = Categoria(nombre=cat)
            db.session.add(c); db.session.flush()
        s = Subcategoria(nombre=sub, categoria_id=c.id)
        db.session.add(s); db.session.flush()
        return s, c.nombre, s.nombre
    return None, c.nombre if c else cat, sub


@reclasificacion_bp.route('/catalogo')
@admin_required
def catalogo():
    return jsonify([{'id': c.id, 'nombre': c.nombre,
                     'subcategorias': [{'id': s.id, 'nombre': s.nombre} for s in
                        sorted(c.subcategorias, key=lambda s: normalizar(s.nombre)) if s.is_active]}
                    for c in Categoria.query.filter_by(is_active=True).order_by(Categoria.nombre).all()])


@reclasificacion_bp.route('', methods=['GET'])
@admin_required
def listar():
    revisiones = RevisionClasificacion.query.order_by(RevisionClasificacion.created_at.desc()).all()
    return jsonify([presentar(r, False) for r in revisiones])


@reclasificacion_bp.route('', methods=['POST'])
@admin_required
def crear():
    filas = []
    for p in Producto.query.order_by(Producto.codigo).all():
        s = p.subcategoria
        filas.append({'id': p.id, 'codigo': p.codigo, 'nombre': p.nombre,
            'subcategoria_id_actual': p.subcategoria_id,
            'categoria_actual': s.categoria.nombre if s else '', 'subcategoria_actual': s.nombre if s else '',
            'categoria_destino': '', 'subcategoria_destino': '', 'destino_id': None,
            'estado': 'sin_revisar', 'motivo': '', 'editada': False, 'aprobada': False})
    r = RevisionClasificacion(creado_por_id=get_jwt_identity(), filas=filas)
    db.session.add(r); db.session.commit()
    return jsonify(presentar(r)), 201


@reclasificacion_bp.route('/<id>', methods=['GET'])
@admin_required
def detalle(id):
    return jsonify(presentar(obtener(id)))


@reclasificacion_bp.route('/<id>/procesar', methods=['POST'])
@admin_required
def procesar(id):
    r = obtener(id)
    if r.bloqueado_hasta > time.time():
        raise Conflicto('Otro lote está en proceso. Recarga dentro de un momento.')
    lote = [f for f in r.filas if f['estado'] == 'sin_revisar'][:10]
    if not lote:
        return jsonify(presentar(r))
    token = str(uuid.uuid4())
    r.token_lote, r.bloqueado_hasta = token, time.time() + 90
    entrada = [{k: f[k] for k in ('codigo', 'nombre', 'categoria_actual', 'subcategoria_actual')} for f in lote]
    catalogo_ia = [{'categoria': c.nombre, 'subcategorias': [s.nombre for s in c.subcategorias if s.is_active]}
                   for c in Categoria.query.filter_by(is_active=True).all()]
    db.session.commit()  # No mantener bloqueos durante la petición a Gemini.
    try:
        respuestas = validar(consultar(entrada, catalogo_ia, web=True), entrada)
    except Exception:
        r = obtener(id)
        if r.token_lote == token:
            r.token_lote, r.bloqueado_hasta = None, 0
            db.session.commit()
        raise ValueError('Gemini no pudo completar el lote. El avance anterior está guardado; pulsa Continuar revisión para reintentar.')
    r = obtener(id)
    if r.token_lote != token:
        raise Conflicto('Este lote fue retomado por otra sesión. Recarga la revisión.')
    filas = deepcopy(r.filas)
    por_codigo = {x['codigo']: x for x in respuestas}
    ids = {f['id'] for f in lote}
    for f in filas:
        if f['id'] not in ids:
            continue
        propuesta = por_codigo[f['codigo']]
        f['motivo'] = propuesta['motivo'][:1000]
        f['estado'] = 'pendiente'
        if propuesta['ambiguo']:
            continue
        try:
            s, cat, sub = resolver(propuesta['categoria'], propuesta['subcategoria'])
            f.update(categoria_destino=cat, subcategoria_destino=sub, destino_id=s.id if s else None)
            f['estado'] = 'correcto' if s and s.id == f['subcategoria_id_actual'] else 'listo' if s else 'nueva'
        except ValueError as error:
            f['motivo'] = str(error)
    r.token_lote, r.bloqueado_hasta = None, 0
    return guardar(r, filas)


@reclasificacion_bp.route('/<id>/editar', methods=['POST'])
@admin_required
def editar(id):
    r, data = obtener(id, True), datos()
    filas = deepcopy(r.filas)
    f = next((f for f in filas if f['id'] == data.get('producto_id')), None)
    if not f or f['estado'] == 'aplicado':
        raise ValueError('Selecciona un producto que aún no haya sido aplicado')
    if data.get('subcategoria_id'):
        s = db.session.get(Subcategoria, data['subcategoria_id'])
        if not s or not s.is_active or not s.categoria.is_active:
            raise ValueError('Selecciona una subcategoría activa')
        cat, sub = s.categoria.nombre, s.nombre
    else:
        s, cat, sub = resolver(data.get('categoria'), data.get('subcategoria'))
    f.update(categoria_destino=cat, subcategoria_destino=sub, destino_id=s.id if s else None,
             editada=True, aprobada=False, motivo='Clasificación seleccionada manualmente por administrador.')
    f['estado'] = 'correcto' if s and s.id == f['subcategoria_id_actual'] else 'listo' if s else 'nueva'
    return guardar(r, filas)


@reclasificacion_bp.route('/<id>/aprobar', methods=['POST'])
@admin_required
def aprobar(id):
    r, data = obtener(id, True), datos()
    cat, sub = nombre(data.get('categoria')), nombre(data.get('subcategoria'))
    filas = deepcopy(r.filas)
    for f in filas:
        if f['estado'] == 'nueva' and (normalizar(f['categoria_destino']), normalizar(f['subcategoria_destino'])) == (normalizar(cat), normalizar(sub)):
            f.update(estado='listo', aprobada=True)
    return guardar(r, filas)


@reclasificacion_bp.route('/<id>/aplicar', methods=['POST'])
@admin_required
def aplicar(id):
    r = obtener(id, True)
    filas = deepcopy(r.filas)
    elegidas = sorted((f for f in filas if f['estado'] == 'listo'), key=lambda f: f['id'])
    for f in elegidas:
        p = Producto.query.filter_by(id=f['id']).with_for_update().first()
        if not p or p.nombre != f['nombre'] or p.subcategoria_id != f['subcategoria_id_actual']:
            raise Conflicto(f"{f['codigo']}: cambió desde la revisión. Genera una nueva revisión; no se aplicó ningún cambio.")
        s, cat, sub = resolver(f['categoria_destino'], f['subcategoria_destino'])
        if s is None:
            if not f['aprobada']:
                raise Conflicto('Falta aprobar un destino nuevo')
            s, cat, sub = resolver(cat, sub, crear=True)
        elif f['destino_id'] and f['destino_id'] != s.id:
            raise Conflicto('El destino cambió desde la revisión. Vuelve a seleccionarlo.')
        p.subcategoria_id = s.id
        f.update(estado='aplicado', aplicado_por=get_jwt_identity(),
                 aplicado_en=get_cdmx_now().isoformat(), subcategoria_id_nueva=s.id)
    return guardar(r, filas)
