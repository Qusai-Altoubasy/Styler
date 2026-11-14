from enum import StrEnum


class OrderStatus(StrEnum):
    """The manager's own mark on an order. NULL means not marked yet.

    Never shown to the customer and never sends anything.
    """

    DONE = "done"
    CANCELLED = "cancelled"
