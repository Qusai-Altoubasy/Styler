"""Replacing a product's quantity table or colors with the list the dashboard sent, as
pure rules without the database.

The dashboard always sends the whole list. A row that carries the `id` of a live row of
the same product updates that row in place, so its id stays the same: a customer's cart
in the storefront refers to tiers and colors by id, and a price change must not break
it. A row without an `id` is new. Live rows missing from the list are removed
(soft-deleted).
"""

from collections.abc import Collection, Hashable, Mapping, Sequence
from typing import NamedTuple

from app.core.errors import InvalidRequestError


class Replacement(NamedTuple):
    removed: list[int]
    """Ids of live rows to soft-delete."""
    updated: list[tuple[int, int]]
    """(id of the live row, index in the sent list) pairs to update in place."""
    added: list[int]
    """Indexes in the sent list to insert as new rows."""


def plan_replacement(
    live_ids: Collection[int], sent_ids: Sequence[int | None], *, row_name: str
) -> Replacement:
    """Which live rows to keep, update or remove, and which sent rows to add.

    An id that is not a live row of this product is `<row_name>_not_found`, and an id
    sent twice is `<row_name>_id_repeated` (both 422, with the row's `index`).
    """
    seen: set[int] = set()
    updated: list[tuple[int, int]] = []
    added: list[int] = []
    for index, row_id in enumerate(sent_ids):
        if row_id is None:
            added.append(index)
            continue
        if row_id not in live_ids:
            raise InvalidRequestError(
                f"{row_name}_not_found", f"Unknown {row_name} id", index=index, id=row_id
            )
        if row_id in seen:
            raise InvalidRequestError(
                f"{row_name}_id_repeated", f"The same {row_name} id was sent twice", index=index
            )
        seen.add(row_id)
        updated.append((row_id, index))
    removed = [row_id for row_id in live_ids if row_id not in seen]
    return Replacement(removed=removed, updated=updated, added=added)


def find_duplicate(keys: Sequence[Hashable]) -> int | None:
    """The index of the first key that repeats an earlier one, or None."""
    seen: set[Hashable] = set()
    for index, key in enumerate(keys):
        if key in seen:
            return index
        seen.add(key)
    return None


def avoid_unique_collisions[K](
    plan: Replacement, live_keys: Mapping[int, K], sent_keys: Sequence[K]
) -> Replacement:
    """The plan, changed so that updating rows in place never breaks a unique index on the
    way, only checked at the end.

    The database checks a unique index after each row's UPDATE. When an updated row takes
    the key another kept row has now (two tiers swapping their quantities), it would
    clash before the other row moves. Such a row is removed and added again instead: it
    gets a new id, which is fine, since it now means something else anyway. The sent
    keys must already be free of duplicates (`find_duplicate`).
    """
    kept_keys = {live_keys[row_id]: row_id for row_id, _ in plan.updated}
    removed = list(plan.removed)
    updated: list[tuple[int, int]] = []
    added = list(plan.added)
    for row_id, index in plan.updated:
        holder = kept_keys.get(sent_keys[index])
        if holder is not None and holder != row_id:
            removed.append(row_id)
            added.append(index)
        else:
            updated.append((row_id, index))
    return Replacement(removed=removed, updated=updated, added=sorted(added))
