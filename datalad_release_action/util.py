def strip_prefix(s: str, prefix: str) -> str:
    # cf. str.removeprefix, introduced in Python 3.9
    """
    If ``s`` starts with ``prefix``, return the rest of ``s`` after ``prefix``;
    otherwise, return ``s`` unchanged.
    """
    n = len(prefix)
    return s[n:] if s[:n] == prefix else s
