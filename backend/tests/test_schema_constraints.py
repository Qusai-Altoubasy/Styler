"""What `alembic check` does not compare: CHECK constraints and enum values.

The migrations hold their own copies of these rules (a migration never imports the
app), so these tests make sure the database built by the migrations still matches
the models: same CHECK constraint names, same enum values, same patterns.
"""

import re

from sqlalchemy import CheckConstraint, Enum, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import conv

from app.models import Base

_QUOTED = re.compile(r"'([^']*)'")


def _model_check_constraints() -> dict[str, CheckConstraint]:
    constraints = {}
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            if isinstance(constraint, CheckConstraint) and constraint.name:
                name = constraint.name
                full_name = str(name) if isinstance(name, conv) else f"ck_{table.name}_{name}"
                constraints[full_name] = constraint
    return constraints


async def _database_check_constraints(session: AsyncSession) -> dict[str, str]:
    rows = await session.execute(
        text(
            "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE contype = 'c' AND conname LIKE 'ck\\_%' "
            "AND connamespace = 'public'::regnamespace"
        )
    )
    return {name: definition for name, definition in rows.all()}


async def test_check_constraint_names_match_the_models(db_session: AsyncSession) -> None:
    in_database = await _database_check_constraints(db_session)

    assert set(in_database) == set(_model_check_constraints())


async def test_enum_values_match_the_models(db_session: AsyncSession) -> None:
    in_database = await _database_check_constraints(db_session)

    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, Enum):
                definition = in_database[f"ck_{table.name}_{column.type.name}"]
                assert set(_QUOTED.findall(definition)) == set(column.type.enums), (
                    f"{table.name}.{column.name}: add a migration for the new enum values"
                )


async def test_check_constraint_literals_match_the_models(db_session: AsyncSession) -> None:
    """Patterns such as the phone and color regexes are the same in both places."""
    in_database = await _database_check_constraints(db_session)

    for name, constraint in _model_check_constraints().items():
        for literal in _QUOTED.findall(str(constraint.sqltext)):
            assert f"'{literal}'" in in_database[name], f"{name}: {literal!r} differs"
