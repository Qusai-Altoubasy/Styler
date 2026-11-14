"""How a product is priced. Shared because orders freeze it on each order item."""

from enum import StrEnum


class PricingMode(StrEnum):
    FIXED = "fixed"  # a table of fixed quantities, each with a price
    QUOTE = "quote"  # no price on the site; priced by hand on WhatsApp
