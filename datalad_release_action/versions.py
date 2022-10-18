from __future__ import annotations
from enum import Enum
from functools import total_ordering
import re
import subprocess
from typing import Optional
from .util import strip_prefix


@total_ordering
class Bump(Enum):
    """
    >>> Bump.MAJOR > Bump.MINOR
    True
    >>> Bump.MINOR > Bump.MAJOR
    False
    >>> Bump.MINOR > Bump.PATCH
    True
    >>> Bump.PATCH > Bump.MINOR
    False
    >>> Bump.MAJOR > Bump.PATCH
    True
    >>> Bump.PATCH > Bump.MAJOR
    False
    """

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"

    def __lt__(self, other: Bump) -> bool:
        return self.level > other.level

    @property
    def level(self) -> int:
        if self is Bump.MAJOR:
            return 0
        elif self is Bump.MINOR:
            return 1
        elif self is Bump.PATCH:
            return 2
        else:
            raise AssertionError(f"Unexpected Bump value: {self!r}")


def bump_version(v: str, bump: Bump) -> str:
    """
    >>> bump_version("0.5.0", Bump.MAJOR)
    '1.0.0'
    >>> bump_version("1", Bump.MAJOR)
    '2'
    >>> bump_version("1.2.3", Bump.MAJOR)
    '2.0.0'
    >>> bump_version("1.2.3.4", Bump.MAJOR)
    '2.0.0.0'
    >>> bump_version("0.5.0", Bump.MINOR)
    '0.6.0'
    >>> bump_version("1", Bump.MINOR)
    '1.1'
    >>> bump_version("1.2.3", Bump.MINOR)
    '1.3.0'
    >>> bump_version("1.2.3.4", Bump.MINOR)
    '1.3.0.0'
    >>> bump_version("0.5.0", Bump.PATCH)
    '0.5.1'
    >>> bump_version("1", Bump.PATCH)
    '1.0.1'
    >>> bump_version("1.2.3", Bump.PATCH)
    '1.2.4'
    >>> bump_version("1.2.3.4", Bump.PATCH)
    '1.2.4.0'
    """
    parts = [int(p) for p in v.split(".")]
    vs = parts + [0] * (bump.level + 1 - len(parts))
    vs[bump.level] += 1
    vs[bump.level + 1 :] = [0] * len(vs[bump.level + 1 :])
    return ".".join(map(str, vs))


def get_highest_version_tag(tag_prefix: str) -> str:
    r = subprocess.run(
        ["git", "tag", "-l", "--merged", "HEAD"],
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    max_version: Optional[tuple[int, ...]] = None
    max_tag: Optional[str] = None
    for tag in r.stdout.splitlines():
        tag = tag.rstrip("\n")
        stripped_tag = strip_prefix(prefix=tag_prefix, s=tag)
        if re.fullmatch(r"\d+(?:\.\d+)*", stripped_tag):
            v = tuple(map(int, stripped_tag.split(".")))
            if max_version is None or v > max_version:
                max_tag = tag
    if max_tag is None:
        raise RuntimeError(
            f"Repository does not have any tags of the form {tag_prefix}N.N.N"
        )
    return max_tag
