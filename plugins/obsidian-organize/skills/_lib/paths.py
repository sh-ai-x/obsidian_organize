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


@dataclass(frozen=True)
class HierarchicalPaths:
    """All paths produced by a single hierarchical promotion.

    ``slug_dir`` is the per-topic directory (e.g. ``wiki/<domain>/<slug>/``
    or ``wiki/<domain>/<major>/<slug>/``). ``sub_hub`` is the
    auto-generated ``<slug>/_index.md``. ``major_hub`` is the optional
    auto-generated ``<major>/_index.md`` (only when ``--major`` is
    passed). ``leaf_dir`` is the directory the per-section leaf notes
    live in (always equal to ``slug_dir``). ``leaf_paths`` is populated
    by :func:`promote` after each leaf note is written.
    """

    slug_dir: Path
    sub_hub: Path
    major_hub: Path | None
    leaf_dir: Path
    leaf_paths: list[Path]


def resolve_hierarchical_paths(
    vault_root: Path,
    topic_slug: str,
    *,
    domain: str,
    major: str | None = None,
) -> HierarchicalPaths:
    """Compute the directory + file paths for a hierarchical promotion.

    Layout:

    - ``--major`` not set: leaves under ``wiki/<domain>/<slug>/<section>.md``,
      sub-hub at ``<slug>/_index.md``.
    - ``--major`` set: leaves under
      ``wiki/<domain>/<major>/<slug>/<section>.md``, sub-hub at
      ``<slug>/_index.md``, major hub at ``<major>/_index.md``.

    The function does **not** create any directories or files; it just
    resolves the paths. Callers are responsible for actually writing.
    """
    base = vault_root / "wiki" / domain
    if major:
        slug_dir = base / major / topic_slug
        major_hub: Path | None = base / major / "_index.md"
    else:
        slug_dir = base / topic_slug
        major_hub = None
    return HierarchicalPaths(
        slug_dir=slug_dir,
        sub_hub=slug_dir / "_index.md",
        major_hub=major_hub,
        leaf_dir=slug_dir,
        leaf_paths=[],
    )


def detect_wiki_domain(vault_root: Path, default: str = "ai-agent-wiki") -> str:
    """Pick the ``<domain>`` for a hierarchical promotion.

    Returns ``default`` if no ``wiki/`` directory exists yet. If
    exactly one ``wiki/<domain>/`` directory exists, returns that
    domain. If multiple exist, the first one in sorted order is
    returned (callers can override explicitly via the ``domain=``
    argument to :func:`promote`).
    """
    wiki = vault_root / "wiki"
    if not wiki.is_dir():
        return default
    candidates = sorted(p for p in wiki.iterdir() if p.is_dir() and not p.name.startswith("."))
    if not candidates:
        return default
    return candidates[0].name


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

