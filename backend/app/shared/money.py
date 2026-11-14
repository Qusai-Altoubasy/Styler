"""Money in Jordanian dinars: Decimal with 3 decimal places (1 JOD = 1000 fils)."""

from sqlalchemy import Numeric

MONEY = Numeric(precision=10, scale=3)
"""Column type for every amount. Up to 9,999,999.999 JOD; never a float."""
