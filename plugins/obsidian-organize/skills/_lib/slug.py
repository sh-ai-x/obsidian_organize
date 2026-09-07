"""Topic slug normalization + validation.

A topic slug is what lives in the file path (`<topic>.md`) and in the
frontmatter `topic:` key. Slugs are constrained so they survive every
common filesystem.
"""

from __future__ import annotations

import re

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_SECTION_TITLE_MAX = 60


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


def section_title_to_slug(title: str) -> str:
    """Convert a section heading (e.g. ``OWASP LLM Top 10 — 2025 Edition``)
    to a kebab-case filename slug, ≤ 60 chars, with no leading number.

    Reuses the same normalization as :func:`normalize_topic_slug` so
    section filenames live under the same character set as topic slugs.
    Trailing punctuation is stripped before normalization. Output is
    guaranteed to match the topic-slug pattern when non-empty.
    """
    s = title.strip()
    # Strip trailing em-dash, en-dash, periods, colons — the heading
    # punctuation is not meaningful in a filename.
    s = s.rstrip(" \t\n:.;—-")
    s = s.lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if not s:
        # Heading was pure punctuation or non-ASCII; fall back to a
        # safe default so the leaf has a usable filename.
        return "section"
    if len(s) > _SECTION_TITLE_MAX:
        s = s[:_SECTION_TITLE_MAX].rstrip("-")
    return s

