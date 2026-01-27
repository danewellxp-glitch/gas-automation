"""
Alembic environment configuration.
Suporta migrações assíncronas com asyncpg.
"""

import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection

# Adicionar o diretório raiz ao path para importar app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.models import Base

# Configuração do Alembic
config = context.config

# Interpretar o arquivo de configuração para logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata dos modelos para autogenerate
target_metadata = Base.metadata

# Sobrescrever URL do banco com a do settings
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """
    Executa migrações em modo 'offline'.

    Gera SQL sem conectar ao banco.
    Útil para revisar as migrações antes de aplicar.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Executa as migrações com a conexão fornecida."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Executa migrações em modo 'online'.
    Conecta ao banco e aplica as migrações.
    """
    # Usar configuração síncrona para migrações
    connectable = create_engine(settings.database_url.replace("+asyncpg", ""))

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
