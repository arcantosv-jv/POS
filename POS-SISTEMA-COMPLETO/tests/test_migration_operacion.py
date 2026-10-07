"""Ejecuta el mismo arranque de migraciones que producción en bases temporales."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime
import sqlalchemy as sa
from models import db

ROOT = Path(__file__).resolve().parents[1]
ADDITIONS = {
    'cierres_caja': {'egresos', 'reembolsos_efectivo'},
    'devoluciones_venta': {'reembolsos', 'caja_empleado_id', 'fecha_movimiento'},
    'reparaciones': {'diagnostico', 'tecnico', 'fecha_prometida', 'anticipo', 'historial'},
}
NEW_TABLES = {'consultas_compatibilidad', 'compatibilidades_verificadas'}


class MigrationTest(unittest.TestCase):
    def test_existing_and_unversioned_databases(self):
        for versioned in (True, False):
            with self.subTest(versioned=versioned), tempfile.TemporaryDirectory() as directory:
                url = 'sqlite:///' + str(Path(directory) / 'migration.sqlite')
                engine = sa.create_engine(url)
                legacy = sa.MetaData()
                for table in db.metadata.sorted_tables:
                    if table.name in NEW_TABLES:
                        continue
                    sa.Table(table.name, legacy, *(col._copy() for col in table.columns if col.name not in ADDITIONS.get(table.name, set())))
                legacy.create_all(engine)
                with engine.begin() as conn:
                    conn.execute(legacy.tables['sucursales'].insert(), dict(id='s', nombre='Prueba', direccion='Centro'))
                    conn.execute(legacy.tables['users'].insert(), dict(id='u', username='admin', email='test@example.com', password_hash='test', role='admin'))
                    conn.execute(legacy.tables['cierres_caja'].insert(), dict(id='c', empleado_id='u', sucursal_id='s', fecha=date.today(), total_ventas=1000, total_efectivo=1000, egreso=200, concepto_egreso='Sueldo', estado='cerrado', efectivo_reportado=800, diferencia=0, created_at=datetime.now()))
                    if versioned:
                        conn.execute(sa.text('CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)'))
                        conn.execute(sa.text("INSERT INTO alembic_version VALUES ('008')"))
                env = {**os.environ, 'DATABASE_URL': url, 'FLASK_ENV': 'development', 'PYTHONWARNINGS': 'ignore', 'PYTHONDONTWRITEBYTECODE': '1'}
                for _ in range(2):
                    result = subprocess.run([sys.executable, 'railway_migrate.py'], cwd=ROOT, env=env, text=True, capture_output=True, timeout=45)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                with engine.connect() as conn:
                    self.assertEqual(conn.execute(sa.text('SELECT version_num FROM alembic_version')).scalar(), '009')
                    row = conn.execute(sa.text('SELECT total_ventas, egreso, concepto_egreso, efectivo_reportado, diferencia, egresos, reembolsos_efectivo FROM cierres_caja WHERE id=\'c\'')).one()
                    self.assertEqual(tuple(row), (1000, 200, 'Sueldo', 800, 0, None, 0))
                    for table, columns in ADDITIONS.items():
                        self.assertFalse(columns - {c['name'] for c in sa.inspect(conn).get_columns(table)})
                    self.assertTrue(NEW_TABLES.issubset(sa.inspect(conn).get_table_names()))
                engine.dispose()


if __name__ == '__main__':
    unittest.main()
