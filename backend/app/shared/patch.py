"""Base of every PATCH body: a field left out is not changed, an explicit `null` is
refused unless the field is listed in `NULLABLE`."""

from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, model_validator


class PatchModel(BaseModel):
    """Declare every field as `X | None = None` and list the ones where `null` means
    "clear it" in `NULLABLE`. Unknown fields are refused. `"name" in model_fields_set`
    tells whether a field was sent."""

    model_config = ConfigDict(extra="forbid")

    NULLABLE: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _refuse_null(self) -> Self:
        for name in self.model_fields_set - self.NULLABLE:
            if getattr(self, name) is None:
                raise ValueError(f"{name} may not be null")
        return self
