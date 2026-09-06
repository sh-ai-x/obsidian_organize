"""Path resolution + back-link scanning helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

BACKLINK_MARKER_TEMPLATE = "<!-- back-linked from [[topics/{topic}]] on {timestamp} -->"


def resolve_staged_path(vault_root: Path, topic: str) -> Path:
    return vault_root / "_research" / f"{topic}.md"


def resolve_topic_path(vault_root: Path, topic: str) -> Path:
    return vault_root / "topics" / f"{topic}.md"


def resolve_archive_path(vault_root: Path, topic: str, now: datetime | None = None) -> Path:
    when = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H-%M-%SZ")
    return vault_root / "_archive" / "research" / f"{topic}-{when}.md"


def safe_filename(name: str) -> str:
    """Strip filesystem-hostile + markdown-hostile characters from a filename.

    Filesystem-hostile (cannot appear in a single path segment on any of
    the platforms we target, plus whitespace which silently breaks shell
    tooling): ``/ \\ : * ? " < > |`` and ``\\n \\r \\t``.

    Markdown-hostile (would break the `[[wikilink]]` / `# heading` /
    backtick inline-code interpolation in `wiki-map.md` and topic
    README pages, or smuggle HTML / wikilink payloads into rendered
    Obsidian output): backtick `` ` ``, ``*``, ``~``, ``_``, ``[``, ``]``,
    ``|``, ``#``. The pipe ``|`` and ``[`` / ``]`` are already in the
    filesystem set; listing them twice is harmless.

    All bad chars collapse to ``-`` so the file extension (``stem.md``)
    is preserved. An empty result falls back to ``untitled.md`` so the
    caller never has to handle a path with no name component.
    """
    bad = set('/\\:*?"<>|\n\r\t`*_~[]#')
    out = "".join("-" if c in bad else c for c in name).strip()
    return out or "untitled.md"


@dataclass(frozen=True)
class BacklinkHit:
    file: Path
    line_no: int  # 1-indexed


_EXCLUDED_DIRS = {
    "topics",
    "_research",
    "_archive",
    ".obsidian",
    ".git",
    "node_modules",
    ".trash",
}


def scan_backlinks(vault_root: Path, topic: str) -> list[BacklinkHit]:
    """Walk the vault (excluding well-known dir names) for the back-link marker.

    Returns the lines (with file + 1-indexed line number) that contain the
    marker for `topic`. The caller decides whether to delete them.

    A file whose contents cannot be decoded as UTF-8 is NOT silently
    skipped: a `logger.warning` naming the file is emitted so callers
    (and post-incident forensics) can see the failure. The scan still
    completes for every other file — a single bad file must not block
    `remove_wiki.retire` from cleaning up back-links in the rest of the
    vault.
    """
    marker = f"[[topics/{topic}]]"
    hits: list[BacklinkHit] = []
    for path in vault_root.rglob("*.md"):
        rel_parts = path.relative_to(vault_root).parts
        if rel_parts and rel_parts[0] in _EXCLUDED_DIRS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            # Do NOT `continue` silently — that previously made the file
            # invisible to `remove_wiki.retire`, which would delete the
            # topic note while leaving back-link markers in this file
            # forever, with no signal to anyone. Surface the failure.
            logger.warning(
                "scan_backlinks: skipping non-UTF-8 file %s: %s",
                path,
                e,
            )
            continue
        except OSError as e:
            # Permission denied / file vanished mid-scan / etc. — also
            # surface, don't silently swallow.
            logger.warning(
                "scan_backlinks: failed to read %s: %s",
                path,
                e,
            )
            continue
        for n, line in enumerate(text.splitlines(), start=1):
            if marker in line and line.lstrip().startswith("<!--"):
                hits.append(BacklinkHit(file=path, line_no=n))
    return hits
