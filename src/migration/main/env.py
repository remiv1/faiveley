"""Script de migration Alembic pour la base métier"""

import sys
import os
import urllib.parse
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import du chemin du projet au sys.path
sys.path.insert(0, "/app")

# Import des modules du projet
from common import WorkingBase# pylint: disable=E0401, C0413
from common.models.articles import *# pylint: disable=E0401, C0413, W0401, W0614
from common.models.employees import *# pylint: disable=E0401, C0413, W0401, W0614
from common.models.posts import *# pylint: disable=E0401, C0413, W0401, W0614
from common.models.ordre_fabrication import *# pylint: disable=E0401, C0413, W0401, W0614
from common.models.machines import *# pylint: disable=E0401, C0413, W0401
from common.models.materials import *# pylint: disable=E0401, C0413, W0401, W0614
from common.models.production import *# pylint: disable=E0401, C0413, W0401, W0614

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config # pylint: disable=E1101

# Création de la chaine de connexion à la base de données
postgres_password_migr_encoded = urllib.parse.quote(
    os.getenv("POSTGRES_PASSWORD_MIGR", ""),
    safe="",
)
database_url = (
    f"postgresql+psycopg2://"
    f"{os.getenv("POSTGRES_USER_MIGR", "")}:"
    f"{postgres_password_migr_encoded}@"
    f"{os.getenv("POSTGRES_HOST", "")}:"
    f"{os.getenv("POSTGRES_PORT", "")}/"
    f"{os.getenv("POSTGRES_DB_MAIN", "")}"
)

# Définir l'URL de la base de données dans la configuration d'Alembic
config.set_main_option("sqlalchemy.url", database_url.replace('%', '%%'))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = WorkingBase.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(  #pylint: disable=E1101
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():   # pylint: disable=E1101
        context.run_migrations()    # pylint: disable=E1101


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(  # pylint: disable=E1101
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema="migr_main",
            version_table="alembic_version",
        )

        with context.begin_transaction():  # pylint: disable=E1101
            context.run_migrations()       # pylint: disable=E1101


if context.is_offline_mode():   # pylint: disable=E1101
    run_migrations_offline()
else:
    run_migrations_online()
