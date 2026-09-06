"""`obsidian-organize:process_clippings` — implementation helpers.

The deterministic parts of the skill live here so tests can drive them
without an LLM in the loop. The LLM-driven bits (deciding what the
topic-README `description:` line should say, summarising the clipping
into a hub page, etc.) are described in `skills/process_clippings/SKILL.md`.

Pipeline
--------
For each `.md` file directly under `<vault>/Clippings/` (excluding
`processed/`):

  1. `extract_topic_slug(text, filename)` → topic
  2. `wiki/<topic>/README.md` is created if missing (LLM-Wiki template).
  3. `wiki/<topic>/clippings/<safe-name>.md` is written with a
     frontmatter envelope (`type: clipping`) + the original body verbatim.
  4. The source file is moved to `Clippings/processed/<safe-name>.md`,
     disambiguated with an ISO-8601 suffix if the target already exists.
  5. A row is appended to `wiki-map.md` (the file is seeded with the
     template if it doesn't exist yet).

The skill is intentionally side-effect-free until step 3 — step 1 reads,
step 2 plans. `--dry-run` short-circuits step 3 onwards.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .frontmatter import serialize_frontmatter
from .slug import normalize_topic_slug


# --------------------------------------------------------------------------- #
# Result types
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ClippingPage:
    """One processed clipping, plus where each artifact landed on disk."""

    source: Path  # original `.md` in `<vault>/Clippings/`
    moved_to: Path  # final path under `<vault>/Clippings/processed/`
    topic: str  # slug derived from H1 / filename
    topic_readme: Path  # `wiki/<topic>/README.md`
    clipping_page: Path  # `wiki/<topic>/clippings/<safe-name>.md`


@dataclass(frozen=True)
class ProcessClippingsResult:
    processed: list[ClippingPage]
    skipped: list[Path]  # e.g. files inside `processed/`


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #


_TOPIC_README_TEMPLATE = """\
# {topic}

> {description} — Karpathy-style LLM Wiki
> Created: {created}

## Contents

- [clippings/](clippings/) — raw research sources indexed here.

---

<!-- obsidian-organize:topic:auto-start -->
<!-- Each row below is appended by obsidian-organize:process_clippings when a new source lands. -->
<!-- Do not edit by hand; re-running `bootstrap --force` re-seeds. -->
<!-- obsidian-organize:topic:auto-end -->
"""


_WIKI_MAP_TEMPLATE = """\
---
type: wiki-map
created: {created}
---

# Wiki Map

<!-- obsidian-organize:wiki-map:auto-start -->
<!-- Each row below is appended by obsidian-organize:add_wiki / process_clippings when a new topic lands. -->
<!-- Do not edit by hand; re-running `bootstrap --force` re-seeds. -->

## Topics

<!-- obsidian-organize:wiki-map:auto-end -->
"""


# --------------------------------------------------------------------------- #
# Pure renderers
# --------------------------------------------------------------------------- #


def render_topic_readme(
    topic: str, created_iso: str, description: str | None = None
) -> str:
    """Render the LLM-Wiki topic README template."""
    desc = description or f"{topic} topic hub"
    return _TOPIC_README_TEMPLATE.format(
        topic=topic, description=desc, created=created_iso
    )


def render_clipping_page(
    source_filename: str,
    topic: str,
    body: str,
    processed_iso: str,
) -> str:
    """Wrap a clipping's body in a frontmatter envelope + return markdown."""
    fm = {
        "type": "clipping",
        "topic": topic,
        "source": source_filename,
        "processed": processed_iso,
    }
    body = body.lstrip("\n")
    return serialize_frontmatter(fm, body)


# --------------------------------------------------------------------------- #
# Path resolution
# --------------------------------------------------------------------------- #


def resolve_topic_dir(vault_root: Path, topic: str) -> Path:
    return vault_root / "wiki" / topic


def resolve_clipping_page(
    vault_root: Path, topic: str, source_filename: str
) -> Path:
    return resolve_topic_dir(vault_root, topic) / "clippings" / _safe_filename(
        source_filename
    )


def resolve_processed_path(vault_root: Path, source_filename: str) -> Path:
    return vault_root / "Clippings" / "processed" / _safe_filename(source_filename)


def unique_processed_path(processed_dir: Path, source_filename: str) -> Path:
    """Return a path under `processed_dir` that does not yet exist.

    If `<safe_filename>` is free, return it unchanged. Otherwise append
    an ISO-8601 suffix to the stem (e.g. `a.md` → `a-20260905T120000Z.md`).
    """
    base = _safe_filename(source_filename)
    candidate = processed_dir / base
    if not candidate.exists():
        return candidate
    stem, dot, ext = base.rpartition(".")
    if not dot:
        stem, ext = base, ""
    else:
        ext = "." + ext
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return processed_dir / f"{stem}-{now}{ext}"


def _safe_filename(name: str) -> str:
    """Strip filesystem-hostile characters from a filename."""
    bad = set('/\\:*?"<>|\n\r\t')
    out = "".join("-" if c in bad else c for c in name).strip()
    return out or "untitled.md"


# --------------------------------------------------------------------------- #
# Topic extraction
# --------------------------------------------------------------------------- #


def extract_topic_slug(text: str, filename: str) -> str:
    """Derive a topic slug from the clipping's first H1 (filename fallback)."""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            heading = line[2:].strip()
            slug = normalize_topic_slug(heading)
            if slug:
                return slug
            break
    # No H1, or H1 collapsed to empty (e.g. non-ASCII only) → fall back to filename.
    stem = Path(filename).stem
    slug = normalize_topic_slug(stem)
    if slug:
        return slug
    # Last resort: keep the original stem but normalize whitespace / underscores
    # to hyphens. Non-ASCII chars (e.g. Korean) survive — they're valid in paths.
    import re

    s = stem.strip()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or stem


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #


def process_clippings(
    vault_root: Path,
    now: datetime | None = None,
    dry_run: bool = False,
) -> ProcessClippingsResult:
    """Process every unprocessed `.md` file under `<vault>/Clippings/`.

    Returns the per-clipping artifacts. When `dry_run` is true, no
    files are written or moved; the returned `ClippingPage` records
    what *would* have happened (with `moved_to` reflecting the planned
    target).
    """
    when = now or datetime.now(timezone.utc)
    when_iso = when.strftime("%Y-%m-%dT%H:%M:%SZ")

    clippings_dir = vault_root / "Clippings"
    if not clippings_dir.exists():
        return ProcessClippingsResult(processed=[], skipped=[])

    candidates = sorted(
        p for p in clippings_dir.iterdir() if p.is_file() and p.suffix == ".md"
    )

    processed: list[ClippingPage] = []
    skipped: list[Path] = []
    topics_seen: set[str] = set()
    processed_dir = clippings_dir / "processed"

    for src in candidates:
        text = src.read_text(encoding="utf-8")
        topic = extract_topic_slug(text, src.name)
        if not topic:
            skipped.append(src)
            continue

        topic_dir = resolve_topic_dir(vault_root, topic)
        clipping_page_path = resolve_clipping_page(vault_root, topic, src.name)

        if not dry_run:
            topic_dir.mkdir(parents=True, exist_ok=True)
            (topic_dir / "clippings").mkdir(parents=True, exist_ok=True)
            if topic not in topics_seen:
                readme = topic_dir / "README.md"
                if not readme.exists():
                    readme.write_text(
                        render_topic_readme(topic=topic, created_iso=when_iso),
                        encoding="utf-8",
                    )
                topics_seen.add(topic)

        page_text = render_clipping_page(
            source_filename=src.name,
            topic=topic,
            body=text,
            processed_iso=when_iso,
        )

        if not dry_run:
            clipping_page_path.write_text(page_text, encoding="utf-8")
            processed_dir.mkdir(parents=True, exist_ok=True)
            moved = unique_processed_path(processed_dir, src.name)
            src.rename(moved)
        else:
            moved = processed_dir / _safe_filename(src.name)

        if not dry_run:
            _append_wiki_map_row(vault_root, topic, src.name)

        processed.append(
            ClippingPage(
                source=src,
                moved_to=moved,
                topic=topic,
                topic_readme=topic_dir / "README.md",
                clipping_page=clipping_page_path,
            )
        )

    return ProcessClippingsResult(processed=processed, skipped=skipped)


def _append_wiki_map_row(vault_root: Path, topic: str, source_filename: str) -> None:
    map_path = vault_root / "wiki-map.md"
    if not map_path.exists():
        created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        map_path.write_text(_WIKI_MAP_TEMPLATE.format(created=created), encoding="utf-8")
    text = map_path.read_text(encoding="utf-8")
    row = f"- [[wiki/{topic}/README|{topic}]] — processed `{source_filename}`"
    end_marker = "<!-- obsidian-organize:wiki-map:auto-end -->"
    if end_marker in text:
        text = text.replace(end_marker, f"{row}\n{end_marker}")
    else:
        text += f"\n{row}\n"
    map_path.write_text(text, encoding="utf-8")