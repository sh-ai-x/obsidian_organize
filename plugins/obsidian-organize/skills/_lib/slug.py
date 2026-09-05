"""Topic slug normalization + validation.

A topic slug is what lives in the file path (`<topic>.md`) and in the
frontmatter `topic:` key. Slugs are constrained so they survive every
common filesystem.
"""

from __future__ import annotations

import re

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def normalize_topic_slug(topic: str) -> str:
    """Lowercase, collapse whitespace and underscores to hyphens, strip edges."""
    s = topic.strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def validate_topic_slug(topic: str) -> None:
    """Raise ValueError if `topic` is not a valid slug."""
    if not _SLUG_RE.match(topic):
        raise ValueError(
            f"invalid topic slug: {topic!r}; must match {_SLUG_RE.pattern}"
        )
