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
        if table.name == 'alembic_version':
            continue
        if not inspector.has_table(table.name):
            missing.append(f'{table.name} (tabla)')
            continue

        existing_columns = {column['name'] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if table.name == 'cierres_caja' and column.name == 'closed_at':
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
        if not any(column['name'] == 'closed_at' for column in inspector.get_columns('cierres_caja')):
            raise RuntimeError('La migración terminó sin crear cierres_caja.closed_at')

    print('Migraciones aplicadas correctamente; cierres_caja.closed_at está disponible.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
