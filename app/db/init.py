import logging

from sqlalchemy import inspect, select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.schema import CreateColumn

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import AuditLog, Client, Contract, ContractTemplate, ContractVersion, NotificationEvent, ProntuarioEntry, Signature, User  # noqa: F401
from app.models.enums import UserRole
from app.services.contract_rendering import DEFAULT_CONTRACT_TITLE, DEFAULT_TEMPLATE_TEXT

logger = logging.getLogger(__name__)

def init_database_schema() -> None:
    """Create missing application tables and validate that the expected schema is available."""
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.database_schema}"'))
            _ensure_postgres_enum_values(connection)
            Base.metadata.create_all(bind=connection, checkfirst=True)
            _add_missing_nullable_columns(connection)

        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names(schema=settings.database_schema))
        expected_tables = {table.name for table in Base.metadata.sorted_tables}
        missing_tables = sorted(expected_tables - existing_tables)
    except SQLAlchemyError as exc:
        logger.exception("Database schema initialization failed")
        raise RuntimeError("Falha ao inicializar o schema do banco de dados") from exc

    if missing_tables:
        raise RuntimeError(f"Tabelas obrigatorias ausentes: {', '.join(missing_tables)}")

    logger.info("Database schema ready with %s tables", len(expected_tables))


def _ensure_postgres_enum_values(connection) -> None:
    if connection.dialect.name != "postgresql":
        return

    enum_exists = connection.scalar(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE n.nspname = :schema_name
                  AND t.typname = 'ibp_user_role'
            )
            """
        ),
        {"schema_name": settings.database_schema},
    )
    if not enum_exists:
        return

    schema_name = settings.database_schema.replace('"', '""')
    for role in UserRole:
        value = role.value.replace("'", "''")
        connection.exec_driver_sql(f'ALTER TYPE "{schema_name}"."ibp_user_role" ADD VALUE IF NOT EXISTS \'{value}\'')


def _add_missing_nullable_columns(connection) -> None:
    """Add newly introduced nullable columns when a table already exists.

    This keeps startup-driven schema creation compatible with the project rule
    of not using manual migrations. Required structural changes still fail fast
    so they are not applied silently in an unsafe way.
    """
    inspector = inspect(connection)
    required_missing: list[str] = []
    preparer = connection.dialect.identifier_preparer

    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name, schema=table.schema):
            continue

        existing_columns = {column["name"] for column in inspector.get_columns(table.name, schema=table.schema)}
        for column in table.columns:
            if column.name in existing_columns:
                continue

            has_default = column.default is not None or column.server_default is not None
            if not column.nullable and not has_default:
                required_missing.append(f"{table.name}.{column.name}")
                continue

            column_ddl = str(CreateColumn(column).compile(dialect=connection.dialect))
            table_name = preparer.format_table(table)
            connection.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {column_ddl}")
            logger.info("Added missing database column %s.%s", table.name, column.name)

    if required_missing:
        raise RuntimeError(
            "Colunas obrigatorias ausentes sem valor padrao: " + ", ".join(sorted(required_missing))
        )


def bootstrap_initial_data() -> None:
    """Create optional first admin and default contract template without manual commands."""
    with SessionLocal() as db:
        if settings.initial_admin_email and settings.initial_admin_password:
            if len(settings.initial_admin_password) < 12:
                raise RuntimeError("INITIAL_ADMIN_PASSWORD deve ter pelo menos 12 caracteres")

            admin = db.scalar(select(User).where(User.email == str(settings.initial_admin_email).lower()))
            if not admin:
                db.add(
                    User(
                        name=settings.initial_admin_name or "Administrador",
                        email=str(settings.initial_admin_email).lower(),
                        password_hash=hash_password(settings.initial_admin_password),
                        role=UserRole.adm,
                        is_active=True,
                    )
                )
                logger.info("Initial admin user created for %s", settings.initial_admin_email)

        db.execute(update(User).where(User.role == UserRole.admin).values(role=UserRole.adm))

        if settings.bootstrap_default_template:
            template = db.scalar(
                select(ContractTemplate).where(ContractTemplate.name == DEFAULT_CONTRACT_TITLE)
            )
            if not template:
                db.add(
                    ContractTemplate(
                        name=DEFAULT_CONTRACT_TITLE,
                        content=DEFAULT_TEMPLATE_TEXT,
                        is_active=True,
                    )
                )
            elif template.content != DEFAULT_TEMPLATE_TEXT:
                template.content = DEFAULT_TEMPLATE_TEXT

        db.commit()


def init_application_database() -> None:
    init_database_schema()
    bootstrap_initial_data()
