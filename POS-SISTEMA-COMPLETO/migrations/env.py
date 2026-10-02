# migrations/env.py

from logging.config import fileConfig
import logging
from flask import current_app
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Leer la configuración
config = context.config

# Interpretar la configuración de logging
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

# Agregar el objeto metadata del modelo para proporcionar soporte para
# 'autogenerate'
def get_db():
    from app import db
    return db

config.set_main_option('sqlalchemy.url',
                       current_app.config.get('SQLALCHEMY_DATABASE_URI'))
target_metadata = get_db().metadata

def run_migrations_offline() -> None:
    """Ejecutar migraciones en modo 'offline'."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecutar migraciones en modo 'online'."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = current_app.config.get(
        "SQLALCHEMY_DATABASE_URI"
    )
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
