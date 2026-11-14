"""Free text typed by a customer or the manager.

PostgreSQL refuses the NUL character in text columns, and no other control character
belongs in a name, an address or a search either. Tab and line breaks are allowed
(a multi-line address). Add `NoControlCharacters` to every free-text field type:

    Address = Annotated[str, StringConstraints(max_length=500), NoControlCharacters]
"""

import re

from pydantic import AfterValidator

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _refuse_control_characters(value: str) -> str:
    if _CONTROL_CHARACTERS.search(value):
        raise ValueError("must not contain control characters")
    return value


NoControlCharacters = AfterValidator(_refuse_control_characters)
