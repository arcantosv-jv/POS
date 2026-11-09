"""Permisos de operación y aislamiento de sucursales, comprobados en cada petición."""
from flask import g, request, jsonify, has_request_context
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria
from models import db, User, Sucursal, Venta, Stock, EntradaInventario, CierreCaja, Reparacion, Comision, DevolucionVenta

CATALOG = {
    'dashboard': ('Dashboard', ['ver', 'analizar']),
    'productos': ('Productos (catálogo global)', ['ver', 'crear', 'editar', 'eliminar', 'importar']),
    'inventario': ('Inventario', ['ver', 'ver_stock', 'entradas', 'ajustar', 'eliminar', 'exportar']),
    'ventas': ('Ventas', ['ver', 'crear', 'editar_pagos']),
    'ventas-del-dia': ('Ventas del día', ['ver']),
    'cierre-caja': ('Realizar cierre de caja', ['ver', 'cerrar', 'corregir']),
    'cierres-caja': ('Consultar cierres de caja', ['ver']),
    'reportes': ('Reportes', ['ver']),
    'reportes-ventas': ('Reportes de ventas', ['ver', 'analizar']),
    'categorias': ('Categorías (globales)', ['ver', 'crear', 'editar', 'eliminar']),
    'subcategorias': ('Subcategorías (globales)', ['ver', 'crear', 'editar', 'eliminar']),
    'devoluciones': ('Devoluciones', ['ver', 'crear', 'eliminar']),
    'compatibilidad': ('Compatibilidad', ['ver', 'buscar', 'verificar', 'eliminar']),
    'reparaciones': ('Reparaciones', ['ver', 'crear', 'editar', 'eliminar', 'entregar', 'catalogo']),
    'apartados': ('Apartados', ['ver', 'crear', 'abonar', 'entregar']),
    'comisiones': ('Comisiones', ['ver', 'crear', 'editar', 'eliminar']),
    'ayuda': ('Ayuda', ['consultar']),
    'ventas-sin-stock': ('Ventas sin stock', ['ver']),
}
LEGACY = {
    'ventas': ['ver', 'crear', 'editar_pagos'], 'ventas-del-dia': ['ver'],
    'cierre-caja': ['ver', 'cerrar', 'corregir'],
    'compatibilidad': ['ver', 'buscar', 'verificar', 'eliminar'],
    'reparaciones': ['ver', 'crear', 'editar'], 'comisiones': ['ver', 'crear', 'editar', 'eliminar'],
    'ayuda': ['consultar'],
}


def effective_permissions(user):
    if user.role == 'admin':
        return {key: actions for key, (_, actions) in CATALOG.items()}
    return LEGACY if user.permisos is None else user.permisos


def allowed_branches(user):
    if user.sucursales_permitidas is None:
        return [user.sucursal_id] if user.sucursal_id else []
    return user.sucursales_permitidas


def current_branch(user):
    return request.headers.get('X-Sucursal-Id') or user.sucursal_id if has_request_context() else user.sucursal_id


def can(user, module, action=None):
    if user.role == 'admin':
        return True
    actions = effective_permissions(user).get(module, [])
    return bool(actions) if action is None else action in actions


def validate_access(data, primary_branch):
    permissions = data.get('permisos', {})
    branches = data.get('sucursales_permitidas', [primary_branch] if primary_branch else [])
    if not isinstance(permissions, dict) or set(permissions) - set(CATALOG):
        raise ValueError('Apartados de permisos inválidos')
    for module, actions in permissions.items():
        if not isinstance(actions, list) or any(not isinstance(a, str) or a not in CATALOG[module][1] for a in actions):
            raise ValueError('Acciones inválidas en ' + module)
        if actions and module != 'ayuda' and 'ver' not in actions:
            raise ValueError('Selecciona Ver para habilitar acciones en ' + module)
    if not isinstance(branches, list) or not branches or any(not isinstance(b, str) for b in branches):
        raise ValueError('Selecciona al menos una sucursal')
    if primary_branch not in branches:
        raise ValueError('La sucursal principal debe estar incluida entre las permitidas')
    existing = {b.id for b in Sucursal.query.filter(Sucursal.id.in_(branches), Sucursal.is_active.is_(True)).all()}
    if existing != set(branches):
        raise ValueError('Una de las sucursales no existe o está inactiva')
    return {m: list(dict.fromkeys(a)) for m, a in permissions.items() if a}, list(dict.fromkeys(branches))


# Cada ruta delegable tiene una acción explícita; las no enumeradas son exclusivas de admin.
ENDPOINTS = {}
def route(module, action, *names):
    for name in names:
        ENDPOINTS[name] = (module, action)

route('inventario', 'ver_stock', 'inventario.get_stock_sucursal', 'inventario.get_bajo_stock')
route('inventario', 'ver', 'inventario.get_entradas_inventario')
route('inventario', 'entradas', 'inventario.registrar_entrada_inventario')
route('inventario', 'ajustar', 'inventario.update_stock')
route('inventario', 'eliminar', 'inventario.delete_stock')
route('inventario', 'exportar', 'inventario.exportar_inventario')
for resource, singular in [('productos', 'producto'), ('categorias', 'categoria'), ('subcategorias', 'subcategoria')]:
    route(resource, 'ver', 'productos.get_' + resource, 'productos.get_' + singular)
    for action, prefix in [('crear', 'create_'), ('editar', 'update_'), ('eliminar', 'delete_')]:
        route(resource, action, 'productos.' + prefix + singular)
route('productos', 'ver', 'productos.search_productos')
route('productos', 'importar', 'importar.importar_productos')
route('ventas', 'ver', 'ventas.get_ventas', 'ventas.get_venta', 'ventas.get_ticket', 'ventas.validar_stock')
route('ventas', 'crear', 'ventas.crear_venta')
route('ventas', 'editar_pagos', 'ventas.guardar_pagos_venta')
route('ventas-del-dia', 'ver', 'ventas.get_ventas_del_dia')
route('cierre-caja', 'ver', 'ventas.get_cierre_caja_hoy')
route('cierre-caja', 'cerrar', 'ventas.crear_cierre_caja', 'ventas.iniciar_nuevo_cierre')
route('cierre-caja', 'corregir', 'ventas.corregir_cierre_caja')
route('cierres-caja', 'ver', 'ventas.reportes_cierres_caja', 'ventas.reportes_cierres_caja_detalle')
route('reportes-ventas', 'ver', 'ventas.reportes_por_fecha', 'reportes.ventas_categorias')
route('ventas-sin-stock', 'ver', 'ventas.get_ventas_sin_stock')
for name in ('ventas_diarias', 'ventas_mensuales', 'ventas_anuales', 'productos_vendidos', 'productos_bajo_stock', 'total_productos'):
    route('reportes', 'ver', 'reportes.reportes_' + name)
route('reportes', 'ver', 'reportes.reporte_consolidado')
route('dashboard', 'ver', 'reportes.dashboard_ventas')
route('dashboard', 'analizar', 'reportes.analizar_dashboard_ventas')
route('devoluciones', 'ver', 'devoluciones.obtener_ventas_del_dia', 'devoluciones.listar_devoluciones')
route('devoluciones', 'crear', 'devoluciones.crear_devolucion')
route('devoluciones', 'eliminar', 'devoluciones.cancelar_devolucion')
route('compatibilidad', 'buscar', 'compatibilidad.buscar_compatibilidad')
route('compatibilidad', 'ver', 'compatibilidad.historial_consultas')
route('compatibilidad', 'verificar', 'compatibilidad.verificar_compatibilidad')
route('compatibilidad', 'eliminar', 'compatibilidad.retirar_verificacion')
route('reparaciones', 'ver', 'reparaciones.get_reparaciones', 'reparaciones.get_reparacion')
route('reparaciones', 'crear', 'reparaciones.create_reparacion')
route('reparaciones', 'editar', 'reparaciones.update_reparacion')
route('reparaciones', 'eliminar', 'reparaciones.delete_reparacion')
route('reparaciones', 'entregar', 'reparaciones.marcar_como_entregada')
for resource, singular in [('marcas', 'marca'), ('modelos', 'modelo'), ('tipos', 'tipo'), ('catalogo', 'catalogo_item')]:
    route('reparaciones', 'ver', 'reparaciones.get_' + resource)
    for verb in ('create_', 'update_', 'delete_'):
        route('reparaciones', 'catalogo', 'reparaciones.' + verb + singular)
route('ayuda', 'consultar', 'ayuda.obtener_solucion')


def endpoint_allowed(user):
    if user.role == 'admin':
        return True
    endpoint = request.endpoint
    if endpoint in ('auth.get_profile', 'auth.change_password', 'caracteristicas.acceso', 'admin.get_sucursales_publico', 'permisos.mi_acceso'):
        return True
    if endpoint == 'reportes.ventas_categorias':
        return can(user, 'reportes', 'ver') or can(user, 'reportes-ventas', 'ver')
    if endpoint == 'caracteristicas.panel_ventas':
        return can(user, 'ventas', 'ver')
    if endpoint == 'apartados.registros':
        return can(user, 'apartados', 'ver' if request.method == 'GET' else 'crear')
    if endpoint == 'apartados.operar':
        return can(user, 'apartados', (request.view_args or {}).get('accion')) and (request.view_args or {}).get('accion') in ('abonar', 'entregar')
    if endpoint in ('comisiones.registros', 'comisiones.modificar'):
        return can(user, 'comisiones', {'GET': 'ver', 'POST': 'crear', 'PUT': 'editar', 'DELETE': 'eliminar'}[request.method])
    requirement = ENDPOINTS.get(endpoint)
    if not requirement:
        return False
    module, action = requirement
    if module == 'inventario' and action in ('exportar', 'ajustar', 'eliminar'):
        return can(user, module, action) and can(user, module, 'ver_stock')
    # Catálogos de referencia para formularios; no conceden permisos de escritura.
    if request.method == 'GET' and endpoint.startswith('productos.'):
        return any(can(user, m) for m in ('productos', 'inventario', 'ventas', 'categorias', 'subcategorias', 'reparaciones', 'devoluciones', 'apartados'))
    if endpoint in ('ventas.get_ticket', 'ventas.get_venta'):
        return any(can(user, m, 'ver') for m in ('ventas', 'ventas-del-dia', 'devoluciones'))
    if endpoint in ('reportes.reportes_total_productos', 'reportes.reportes_productos_bajo_stock'):
        return can(user, 'reportes', 'ver') or can(user, 'dashboard', 'ver')
    if module == 'reportes' and action == 'ver':
        return can(user, 'reportes', 'ver') or can(user, 'dashboard', 'ver')
    if endpoint == 'ventas.reportes_cierres_caja':
        return can(user, 'cierres-caja', 'ver') or can(user, 'reportes-ventas', 'ver')
    if module == 'dashboard':
        return can(user, module, action) or can(user, 'reportes-ventas', action)
    return can(user, module, action)


def delegated_access():
    user = getattr(g, 'access_user', None)
    return bool(user and user.permisos is not None and endpoint_allowed(user))


def authorize_request():
    g.pop('access_branches', None)
    g.pop('access_user', None)
    if request.method == 'OPTIONS' or request.endpoint == 'auth.login':
        return
    verify_jwt_in_request()
    user = db.session.get(User, get_jwt_identity())
    if not user or not user.is_active:
        return jsonify({'error': 'Usuario inactivo o no encontrado'}), 401
    g.access_user = user
    if user.role == 'admin':
        return
    if request.endpoint in ('auth.register', 'permisos.usuario_permisos') or (user.permisos is not None and not endpoint_allowed(user)):
        return jsonify({'error': 'No tienes permiso para esta acción'}), 403
    branches = allowed_branches(user)
    data = request.get_json(silent=True) or {}
    ids = [request.headers.get('X-Sucursal-Id'), request.args.get('sucursal_id'), (request.view_args or {}).get('sucursal_id')]
    if isinstance(data, dict):
        ids.append(data.get('sucursal_id'))
    if request.endpoint in ('permisos.mi_acceso', 'caracteristicas.acceso', 'auth.get_profile'):
        ids = []
    if any(branch and branch not in branches for branch in ids):
        return jsonify({'error': 'No tienes acceso a esa sucursal'}), 403
    if request.endpoint == 'importar.importar_productos' and isinstance(data, dict):
        for item in data.get('productos', []):
            if not isinstance(item, dict):
                return jsonify({'error': 'Producto inválido'}), 400
            if item.get('sucursal_id') and item['sucursal_id'] not in branches:
                return jsonify({'error': 'La importación contiene una sucursal no autorizada'}), 403
            if (item.get('sucursal_id') or item.get('stock')) and not can(user, 'inventario', 'ajustar'):
                return jsonify({'error': 'Importar existencias requiere permiso para ajustar inventario'}), 403
    # Legacy conserva sus controles originales; usuarios configurados se aíslan
    # también en relaciones y consultas agregadas mediante criterios SQL.
    if user.permisos is not None:
        g.access_branches = tuple(branches)
        resources = {'stock_id': Stock, 'venta_id': Venta, 'reparacion_id': Reparacion, 'registro_id': Comision}
        for key, model in resources.items():
            value = (request.view_args or {}).get(key)
            if key == 'registro_id' and request.blueprint != 'comisiones':
                continue
            if value and not model.query.filter(model.id == value, model.sucursal_id.in_(branches)).first():
                return jsonify({'error': 'Registro no encontrado en tus sucursales'}), 404
        # Cierre y devolución reciben identificadores también en el cuerpo.
        if isinstance(data, dict) and data.get('venta_id') and request.blueprint == 'devoluciones':
            if not Venta.query.filter(Venta.id == data['venta_id'], Venta.sucursal_id.in_(branches)).first():
                return jsonify({'error': 'Venta no encontrada en tus sucursales'}), 404
        if (request.view_args or {}).get('devolucion_id'):
            if not DevolucionVenta.query.join(Venta).filter(DevolucionVenta.id == request.view_args['devolucion_id'], Venta.sucursal_id.in_(branches)).first():
                return jsonify({'error': 'Devolución no encontrada en tus sucursales'}), 404


@event.listens_for(Session, 'do_orm_execute')
def scope_branch_queries(execute_state):
    if not has_request_context() or not execute_state.is_select or not hasattr(g, 'access_branches'):
        return
    branches = g.access_branches
    statement = execute_state.statement
    for model in (Venta, Stock, EntradaInventario, CierreCaja, Reparacion, Comision):
        statement = statement.options(with_loader_criteria(model, model.sucursal_id.in_(branches), include_aliases=True))
    statement = statement.options(with_loader_criteria(Sucursal, Sucursal.id.in_(branches), include_aliases=True))
    statement = statement.options(with_loader_criteria(DevolucionVenta,
        DevolucionVenta.venta.has(Venta.sucursal_id.in_(branches)), include_aliases=True))
    execute_state.statement = statement


@event.listens_for(Session, 'before_flush')
def protect_branch_writes(session, flush_context, instances):
    if not has_request_context() or not hasattr(g, 'access_branches'):
        return
    for row in session.new.union(session.dirty).union(session.deleted):
        if isinstance(row, (Venta, Stock, EntradaInventario, CierreCaja, Reparacion, Comision)) and row.sucursal_id not in g.access_branches:
            raise ValueError('No tienes acceso para modificar registros de esa sucursal')
