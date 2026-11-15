"""Replacing a quantity table or color list: pure rules, no database."""

import pytest

from app.core.errors import InvalidRequestError
from app.features.catalog.row_replacement import (
    Replacement,
    avoid_unique_collisions,
    find_duplicate,
    plan_replacement,
)


def test_sent_ids_are_updated_new_rows_added_and_missing_ones_removed() -> None:
    plan = plan_replacement({1, 2, 3}, [3, None, 1], row_name="color")

    assert plan == Replacement(removed=[2], updated=[(3, 0), (1, 2)], added=[1])


def test_an_id_of_another_product_is_refused() -> None:
    with pytest.raises(InvalidRequestError) as error:
        plan_replacement({1}, [1, 9], row_name="price_tier")

    assert error.value.code == "price_tier_not_found"
    assert error.value.details == {"index": 1, "id": 9}


def test_an_id_sent_twice_is_refused() -> None:
    with pytest.raises(InvalidRequestError) as error:
        plan_replacement({1}, [1, 1], row_name="color")

    assert error.value.code == "color_id_repeated"


def test_find_duplicate_returns_the_index_of_the_repeat() -> None:
    assert find_duplicate([(1, None, None), (2, None, None)]) is None
    assert find_duplicate([(1, "a", None), (2, None, None), (1, "a", None)]) == 2


def test_rows_swapping_keys_are_re_added_instead_of_updated() -> None:
    plan = Replacement(removed=[], updated=[(1, 0), (2, 1)], added=[])
    live = {1: (100, None, None), 2: (200, None, None)}

    safe = avoid_unique_collisions(plan, live, [(200, None, None), (100, None, None)])

    assert safe == Replacement(removed=[1, 2], updated=[], added=[0, 1])


def test_a_row_moving_to_a_free_key_keeps_its_id() -> None:
    plan = Replacement(removed=[3], updated=[(1, 0), (2, 1)], added=[])
    live = {1: (100, None, None), 2: (200, None, None), 3: (300, None, None)}

    # 1 takes 300, which the removed row 3 frees first; 2 only changes its price.
    safe = avoid_unique_collisions(plan, live, [(300, None, None), (200, None, None)])

    assert safe == plan
