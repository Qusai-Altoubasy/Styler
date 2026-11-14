"""Jordanian mobile numbers: 10 digits starting with 077, 078 or 079."""

import re

JORDAN_MOBILE_PATTERN = r"^07[789][0-9]{7}$"
"""Used by the API validation and by the database CHECK constraints alike."""

JORDAN_COUNTRY_CODE = "962"

_TO_ASCII_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
"""Arabic-Indic and Persian digits, the default on many Arabic phone keyboards."""

_SEPARATORS = re.compile(r"[\s-]")


def normalize_phone(typed: str) -> str:
    """The number as stored: ASCII digits only, without spaces or dashes.

    "٠٧٩ ١٢٣-٤٥٦٧" -> "0791234567". The result is then checked against the pattern.
    """
    return _SEPARATORS.sub("", typed.translate(_TO_ASCII_DIGITS))


def to_international(local_number: str) -> str:
    """07XXXXXXXX -> 9627XXXXXXXX, the form wa.me links need."""
    return JORDAN_COUNTRY_CODE + local_number.removeprefix("0")
