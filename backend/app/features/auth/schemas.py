"""Login and password bodies.

Passwords are taken exactly as typed: never trimmed or normalized, so a space at the
end is part of the password. Only the length is bounded.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

Password = Annotated[str, StringConstraints(min_length=1, max_length=MAX_PASSWORD_LENGTH)]
"""A password being checked: any length that could have been set."""

NewPassword = Annotated[
    str, StringConstraints(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
]
"""A password being set."""


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: Password


class PasswordChangeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: Password
    new_password: NewPassword


class SessionOut(BaseModel):
    expires_at: datetime
