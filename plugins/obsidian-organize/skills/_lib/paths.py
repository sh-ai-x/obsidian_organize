"""Path resolution + back-link scanning helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

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
    """
    marker = f"[[topics/{topic}]]"
    hits: list[BacklinkHit] = []
    for path in vault_root.rglob("*.md"):
        rel_parts = path.relative_to(vault_root).parts
        if rel_parts and rel_parts[0] in _EXCLUDED_DIRS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for n, line in enumerate(text.splitlines(), start=1):
            if marker in line and line.lstrip().startswith("<!--"):
                hits.append(BacklinkHit(file=path, line_no=n))
    return hits
