from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from app.shared.money import MoneyIn
from app.shared.patch import PatchModel


class Amount(BaseModel):
    value: MoneyIn


@pytest.mark.parametrize(
    ("typed", "stored"),
    [("4", "4.000"), ("2.5", "2.500"), ("0", "0.000"), ("9999999.999", "9999999.999")],
)
def test_money_is_quantized_to_three_places(typed: str, stored: str) -> None:
    assert str(Amount(value=Decimal(typed)).value) == stored


@pytest.mark.parametrize("typed", ["-0.001", "1.2345", "10000000", "NaN", "Infinity"])
def test_money_refuses_bad_amounts(typed: str) -> None:
    with pytest.raises(ValidationError):
        Amount.model_validate({"value": typed})


class Patch(PatchModel):
    NULLABLE = frozenset({"note"})

    name: str | None = None
    note: str | None = None


def test_patch_tracks_sent_fields() -> None:
    patch = Patch.model_validate({"note": None})

    assert patch.model_fields_set == {"note"}


def test_patch_refuses_null_unless_nullable() -> None:
    with pytest.raises(ValidationError, match="name may not be null"):
        Patch.model_validate({"name": None})


def test_patch_refuses_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Patch.model_validate({"other": 1})
