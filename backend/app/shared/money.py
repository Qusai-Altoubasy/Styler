"""Money in Jordanian dinars: Decimal with 3 decimal places (1 JOD = 1000 fils)."""

from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, Field
from sqlalchemy import Numeric

MONEY = Numeric(precision=10, scale=3)
"""Column type for every amount. Up to 9,999,999.999 JOD; never a float."""

MAX_AMOUNT = Decimal("9999999.999")
"""The largest amount a MONEY column (NUMERIC(10, 3)) can hold."""


def _three_places(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.001"))


MoneyIn = Annotated[
    Decimal,
    Field(ge=0, max_digits=10, decimal_places=3, allow_inf_nan=False),
    AfterValidator(_three_places),
]
"""A non-negative amount typed by the manager or a visitor: at most 3 places and at most
9,999,999.999, so it always fits the column. "4" becomes 4.000."""
