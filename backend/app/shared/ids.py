"""Database ids as they arrive in a request.

Every id column is a PostgreSQL `integer` (int4). A larger number would make the
driver fail inside the query (a 500), so the API refuses it up front (a 422).
"""

from typing import Annotated

from fastapi import Path
from pydantic import Field

MAX_DB_ID = 2**31 - 1

DbId = Annotated[int, Field(ge=1, le=MAX_DB_ID)]
"""An id in a request body or query string."""

PathId = Annotated[int, Path(ge=1, le=MAX_DB_ID)]
"""An id in the URL path, e.g. `/products/{product_id}`."""
