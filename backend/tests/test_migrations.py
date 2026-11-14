from alembic import command
from tests.conftest import alembic_config


def test_models_and_migrations_match() -> None:
    """Fails when a model changed without a migration (`alembic check`)."""
    command.check(alembic_config())
