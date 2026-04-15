import logging

from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import AuditLog, Client, Contract, ContractTemplate, ContractVersion, NotificationEvent, Signature, User  # noqa: F401
from app.models.enums import UserRole

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATE = """CONTRATO DE PRESTACAO DE SERVICOS DE ATENDIMENTO PSIQUIATRICO

Pelo presente instrumento, as partes identificadas concordam com as condicoes de atendimento, sigilo profissional, responsabilidades, agendamento, cancelamento e demais orientacoes clinicas informadas pelo consultorio.

O paciente declara ter lido e compreendido o conteudo deste documento antes da assinatura.
"""


def init_database_schema() -> None:
    """Create missing application tables and validate that the expected schema is available."""
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        expected_tables = set(Base.metadata.tables.keys())
        missing_tables = sorted(expected_tables - existing_tables)
    except SQLAlchemyError as exc:
        logger.exception("Database schema initialization failed")
        raise RuntimeError("Falha ao inicializar o schema do banco de dados") from exc

    if missing_tables:
        raise RuntimeError(f"Tabelas obrigatorias ausentes: {', '.join(missing_tables)}")

    logger.info("Database schema ready with %s tables", len(expected_tables))


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
                        role=UserRole.admin,
                        is_active=True,
                    )
                )
                logger.info("Initial admin user created for %s", settings.initial_admin_email)

        if settings.bootstrap_default_template:
            template = db.scalar(
                select(ContractTemplate).where(ContractTemplate.name == "Contrato de Atendimento Psiquiatrico")
            )
            if not template:
                db.add(
                    ContractTemplate(
                        name="Contrato de Atendimento Psiquiatrico",
                        content=DEFAULT_TEMPLATE,
                        is_active=True,
                    )
                )

        db.commit()


def init_application_database() -> None:
    init_database_schema()
    bootstrap_initial_data()
