"""Apply database migrations safely for Railway deployments."""
import subprocess
import sys

from sqlalchemy import inspect

from app import app
from models import db


def _legacy_schema_matches_current_models():
    inspector = inspect(db.engine)
    missing = []

    for table in db.metadata.sorted_tables:
        if table.name in {'alembic_version', 'consultas_compatibilidad', 'compatibilidades_verificadas', 'configuracion_sistema', 'comisiones', 'apartados', 'revisiones_clasificacion', 'reglas_costos', 'revisiones_costos', 'empleados_comisiones', 'pagos_comisiones', 'pronostico_estados', 'pronostico_resumenes', 'pronostico_historicos', 'pronosticos'}:
            continue
        if not inspector.has_table(table.name):
            missing.append(f'{table.name} (tabla)')
            continue

        existing_columns = {column['name'] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            additions = {
                'stocks': {'reservado'},
                'productos': {'costo_compra'},
                'detalles_venta': {'costo_compra_unitario'},
                'users': {'permisos', 'sucursales_permitidas'},
                'cierres_caja': {'closed_at', 'egreso', 'concepto_egreso', 'egresos', 'reembolsos_efectivo', 'efectivo_inicial'},
                'devoluciones_venta': {'reembolsos', 'caja_empleado_id', 'fecha_movimiento', 'cierre_caja_id'},
                'ventas': {'cierre_caja_id', 'ediciones'},
                'reparaciones': {'diagnostico', 'tecnico', 'fecha_prometida', 'anticipo', 'historial'},
            }
            if column.name in additions.get(table.name, set()):
                continue
            if column.name not in existing_columns:
                missing.append(f'{table.name}.{column.name}')

    if missing:
        print(
            'No se puede adoptar esta base como revisión 006; faltan elementos de esquema: '
            + ', '.join(missing),
            file=sys.stderr,
        )
        return False
    return True


def _run_flask_migration(*arguments):
    subprocess.run(
        [sys.executable, '-m', 'flask', '--app', 'app', 'db', *arguments],
        check=True,
    )


def main():
    with app.app_context():
        inspector = inspect(db.engine)
        has_alembic_version = inspector.has_table('alembic_version')

        if not has_alembic_version:
            if not _legacy_schema_matches_current_models():
                return 1
            print('Base heredada detectada; registrando esquema validado hasta revisión 006.')
            _run_flask_migration('stamp', '006')
        else:
            print('Historial Alembic detectado; aplicando revisiones pendientes.')

    _run_flask_migration('upgrade')

    with app.app_context():
        inspector = inspect(db.engine)
        columns = {column['name'] for column in inspector.get_columns('cierres_caja')}
        missing = {'closed_at', 'egreso', 'concepto_egreso', 'egresos', 'reembolsos_efectivo', 'efectivo_inicial'} - columns
        if missing:
            raise RuntimeError('La migración terminó sin crear columnas de cierre: ' + ', '.join(sorted(missing)))

        if not _legacy_schema_matches_current_models():
            raise RuntimeError('El esquema no coincide con los modelos')
        for table, required in {
            'reglas_costos': {'id', 'nombre', 'criterio', 'costo', 'activa', 'version'},
            'revisiones_costos': {'id', 'filas', 'version', 'token_lote', 'bloqueado_hasta'},
            'pronostico_estados': {'sucursal_id', 'pendiente', 'actualizado'},
            'pronostico_resumenes': {'sucursal_id', 'fecha', 'categoria_id', 'importe', 'unidades'},
            'pronostico_historicos': {'sucursal_id', 'mes', 'categorias', 'cambios', 'actualizado'},
            'pronosticos': {'id', 'creado_por_id', 'created_at', 'sucursales', 'inicio', 'fin', 'resultado', 'explicacion'},
            'empleados_comisiones': {'id', 'nombre', 'sucursal_id', 'dia_pago', 'activo'},
            'pagos_comisiones': {'id', 'empleado_id', 'sucursal_id', 'empleado_nombre', 'usuario_id', 'usuario_nombre', 'desde', 'hasta', 'fecha_pago', 'monto', 'detalles'},
            'comisiones': {'empleado_comision_id', 'pago_comision_id', 'detalle_venta_id', 'unidad', 'fecha_venta', 'producto_nombre', 'numero_venta'},
            'stocks': {'reservado'},
                'productos': {'costo_compra'},
                'detalles_venta': {'costo_compra_unitario'},
                'users': {'permisos', 'sucursales_permitidas'},
            'devoluciones_venta': {'reembolsos', 'caja_empleado_id', 'fecha_movimiento', 'cierre_caja_id'},
                'ventas': {'cierre_caja_id', 'ediciones'},
            'reparaciones': {'diagnostico', 'tecnico', 'fecha_prometida', 'anticipo', 'historial'},
        }.items():
            if required - {c['name'] for c in inspector.get_columns(table)}:
                raise RuntimeError('Migración incompleta: ' + table)
        if not {'comisiones_habilitadas', 'apartados_habilitados'}.issubset({c['name'] for c in inspector.get_columns('configuracion_sistema')}):
            raise RuntimeError('Migración incompleta: comisiones_habilitadas')
        for table in ('consultas_compatibilidad', 'compatibilidades_verificadas', 'configuracion_sistema', 'comisiones', 'apartados', 'revisiones_clasificacion', 'reglas_costos', 'revisiones_costos', 'empleados_comisiones', 'pagos_comisiones', 'pronostico_estados', 'pronostico_resumenes', 'pronostico_historicos', 'pronosticos'):
            if not inspector.has_table(table):
                raise RuntimeError('Migración incompleta: ' + table)

    print('Migraciones aplicadas correctamente; esquema de operación y seguimiento verificado.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
