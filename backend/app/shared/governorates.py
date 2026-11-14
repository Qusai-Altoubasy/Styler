"""The 12 governorates of Jordan and their delivery zones.

Fixed in code, not a table: they never change, and the delivery fee of each zone
is the part the manager edits (in `settings`).
"""

from enum import StrEnum


class DeliveryZone(StrEnum):
    A = "a"  # Amman and Zarqa
    B = "b"  # every other governorate


class Governorate(StrEnum):
    AMMAN = "amman"
    ZARQA = "zarqa"
    IRBID = "irbid"
    BALQA = "balqa"
    MADABA = "madaba"
    MAFRAQ = "mafraq"
    JERASH = "jerash"
    AJLOUN = "ajloun"
    KARAK = "karak"
    TAFILAH = "tafilah"
    MAAN = "maan"
    AQABA = "aqaba"

    @property
    def zone(self) -> DeliveryZone:
        if self in (Governorate.AMMAN, Governorate.ZARQA):
            return DeliveryZone.A
        return DeliveryZone.B
