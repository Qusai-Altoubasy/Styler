"""Safe substring search with ILIKE."""

LIKE_ESCAPE = "\\"


def contains_pattern(text: str) -> str:
    """`%text%` with the LIKE wildcards in `text` escaped, so `50%` matches literally.

    Use with `.ilike(pattern, escape=LIKE_ESCAPE)`.
    """
    escaped = (
        text.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", LIKE_ESCAPE + "%")
        .replace("_", LIKE_ESCAPE + "_")
    )
    return f"%{escaped}%"
