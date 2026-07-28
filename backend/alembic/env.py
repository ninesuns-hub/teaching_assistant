from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from database.mysql_db import Base, SQLALCHEMY_DATABASE_URL


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option(
    "sqlalchemy.url",
    SQLALCHEMY_DATABASE_URL.render_as_string(hide_password=False).replace("%", "%%"),
)
target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to):
    # Imported teaching databases can contain legacy tables, columns and
    # indexes that are retained for rollback/audit purposes. Alembic manages
    # the current ORM schema without proposing destructive removal of those
    # extra reflected objects.
    if reflected and compare_to is None:
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
