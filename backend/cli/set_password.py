"""Set the manager's password from the server, e.g. when it is forgotten.

There is no email recovery: Qusai runs this on the server. It asks for the password
twice (never on the command line, so it stays out of the shell history) and logs
every device out.

    docker compose ... exec -it api python -m cli.set_password
"""

import asyncio
import getpass

from pydantic import TypeAdapter, ValidationError

from app.core.db import SessionLocal, engine
from app.features.auth import service
from app.features.auth.schemas import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH, NewPassword


def _ask_password() -> str:
    password = getpass.getpass("New manager password: ")
    if getpass.getpass("Repeat it: ") != password:
        raise SystemExit("The two passwords differ. Nothing changed.")
    try:
        return TypeAdapter(NewPassword).validate_python(password)
    except ValidationError:
        raise SystemExit(
            f"Use {MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters. Nothing changed."
        ) from None


async def _save(password: str) -> None:
    async with SessionLocal() as session:
        await service.set_password(session, password)
    await engine.dispose()


def main() -> None:
    asyncio.run(_save(_ask_password()))
    print("Password set. Every device is logged out.")


if __name__ == "__main__":
    main()
