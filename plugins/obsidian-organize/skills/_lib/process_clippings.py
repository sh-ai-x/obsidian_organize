"""`obsidian-organize:process_clippings` — implementation helpers.

The deterministic parts of the skill live here so tests can drive them
without an LLM in the loop. The LLM-driven bits (deciding what the
topic-README `description:` line should say, summarising the clipping
into a hub page, etc.) are described in `skills/process_clippings/SKILL.md`.

Pipeline
--------
For each `.md` file directly under `<vault>/Clippings/` (excluding
`processed/` and dotfiles):

  1. `extract_topic_slug(text, filename)` → topic
  2. `wiki/<topic>/README.md` is created if missing (LLM-Wiki template).
  3. `wiki/<topic>/clippings/<safe-name>.md` is written with a
     frontmatter envelope (`type: clipping`) + the original body verbatim.
  4. A row is appended to `wiki-map.md` (the file is seeded with the
     shared template from `bootstrap` if it doesn't exist yet).
  5. Only after the wiki-map append succeeds, the source file is moved
     to `Clippings/processed/<safe-name>.md` (disambiguated if the
     target already exists). Ordering matters: if step 4 raises, the
     source is still sitting in `Clippings/` and a re-run will pick it
     up again — moving it first would silently lose the clipping.

The skill is intentionally side-effect-free until step 2 — step 1 only
reads. `--dry-run` short-circuits step 2 onwards.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .bootstrap import WIKI_MAP_AUTO_END, WIKI_MAP_AUTO_START, WIKI_MAP_TEMPLATE
from .frontmatter import serialize_frontmatter
from .slug import normalize_topic_slug

logger = logging.getLogger(__name__)


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
    skipped: list[Path]  # e.g. files inside `processed/`, dotfiles, empty topic


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
    If even that timestamped name is taken (two clippings sharing a
    basename processed within the same wall-clock second), an
    incrementing counter is appended until a free path is found — the
    check-then-act race is inherent to any check-before-rename scheme,
    but this at minimum guarantees the loop never returns an occupied
    path.
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
    candidate = processed_dir / f"{stem}-{now}{ext}"
    counter = 1
    while candidate.exists():
        candidate = processed_dir / f"{stem}-{now}-{counter}{ext}"
        counter += 1
    return candidate


def _safe_filename(name: str) -> str:
    """Strip filesystem-hostile characters from a filename."""
    bad = set('/\\:*?"<>|\n\r\t')
    out = "".join("-" if c in bad else c for c in name).strip()
    return out or "untitled.md"


def _sanitize_last_resort_slug(s: str) -> str:
    """Make a last-resort (non-ASCII-preserving) slug safe as a path segment.

    Unlike `normalize_topic_slug` (which is ASCII-only and therefore
    already safe), this branch runs when normalization stripped every
    character — e.g. an H1 or filename stem made entirely of non-ASCII
    text. It must still guarantee the result can never escape the
    `wiki/<topic>/` directory:

    - path separators are never valid inside a single path segment
    - a slug made entirely of dots (`.`, `..`, `...`) resolves to the
      current or parent directory when joined onto a path — CVE-class
      path traversal if left unchecked (`wiki/..` == the vault root).
    """
    s = s.replace("/", "-").replace("\\", "-")
    s = re.sub(r"[\s_]+", "-", s).strip()
    s = re.sub(r"-+", "-", s).strip("-")
    if not s or set(s) <= {"."}:
        return "untitled"
    return s


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
    # Last resort: keep non-ASCII stems (e.g. Korean titles) intact, but
    # never return something that could resolve outside `wiki/<topic>/`.
    return _sanitize_last_resort_slug(stem)


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
        p
        for p in clippings_dir.iterdir()
        if p.is_file() and p.suffix == ".md" and not p.name.startswith(".")
    )

    processed: list[ClippingPage] = []
    skipped: list[Path] = []
    topics_seen: set[str] = set()
    processed_dir = clippings_dir / "processed"

    for src in candidates:
        try:
            text = src.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("skipping %s: failed to read as UTF-8 text: %s", src, e)
            skipped.append(src)
            continue

        topic = extract_topic_slug(text, src.name)
        if not topic:
            logger.warning("skipping %s: could not derive a topic slug", src)
            skipped.append(src)
            continue

        topic_dir = resolve_topic_dir(vault_root, topic)
        clipping_page_path = resolve_clipping_page(vault_root, topic, src.name)

        if not dry_run:
            try:
                topic_dir.mkdir(parents=True, exist_ok=True)
                (topic_dir / "clippings").mkdir(parents=True, exist_ok=True)
                if topic not in topics_seen:
                    readme = topic_dir / "README.md"
                    if not readme.exists():
                        readme.write_text(
                            render_topic_readme(topic=topic, created_iso=when_iso),
                            encoding="utf-8",
                        )
                        logger.info("created topic README: %s", readme)
                    topics_seen.add(topic)
            except OSError as e:
                raise RuntimeError(
                    f"failed to prepare wiki/{topic}/ for clipping {src.name!r}: {e}"
                ) from e

        page_text = render_clipping_page(
            source_filename=src.name,
            topic=topic,
            body=text,
            processed_iso=when_iso,
        )

        if dry_run:
            moved = processed_dir / _safe_filename(src.name)
            processed.append(
                ClippingPage(
                    source=src,
                    moved_to=moved,
                    topic=topic,
                    topic_readme=topic_dir / "README.md",
                    clipping_page=clipping_page_path,
                )
            )
            continue

        try:
            clipping_page_path.write_text(page_text, encoding="utf-8")
            logger.info("wrote clipping page: %s", clipping_page_path)
        except OSError as e:
            raise RuntimeError(
                f"failed to write clipping page for {src.name!r} at "
                f"{clipping_page_path}: {e}"
            ) from e

        # Append the wiki-map row BEFORE moving the source out of
        # Clippings/. If this raises, the source is still sitting in
        # Clippings/ (not yet in processed/), so a re-run will retry
        # this clipping instead of silently losing it — the clipping
        # page and topic README already written are harmless no-ops to
        # recreate.
        try:
            _append_wiki_map_row(vault_root, topic, src.name)
        except OSError as e:
            raise RuntimeError(
                f"failed to update wiki-map.md for topic {topic!r} "
                f"(clipping {src.name!r} left unprocessed for retry): {e}"
            ) from e

        try:
            processed_dir.mkdir(parents=True, exist_ok=True)
            moved = unique_processed_path(processed_dir, src.name)
            src.rename(moved)
            logger.info("archived clipping: %s -> %s", src, moved)
        except OSError as e:
            raise RuntimeError(
                f"failed to archive {src.name!r} to {processed_dir}: {e}"
            ) from e

        processed.append(
            ClippingPage(
                source=src,
                moved_to=moved,
                topic=topic,
                topic_readme=topic_dir / "README.md",
                clipping_page=clipping_page_path,
            )
        )

    if skipped:
        logger.warning("process_clippings: %d file(s) skipped: %s", len(skipped), skipped)

    return ProcessClippingsResult(processed=processed, skipped=skipped)


def _append_wiki_map_row(vault_root: Path, topic: str, source_filename: str) -> None:
    """Append one row to `wiki-map.md`, creating it from the shared template
    if missing. The write is atomic (temp file + `os.replace`) so a crash
    or SIGKILL mid-write can never leave `wiki-map.md` truncated or
    corrupted — the file is either the old complete content or the new
    complete content, never a partial write.
    """
    map_path = vault_root / "wiki-map.md"
    if map_path.exists():
        text = map_path.read_text(encoding="utf-8")
    else:
        created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        text = WIKI_MAP_TEMPLATE.format(
            created=created,
            WIKI_MAP_AUTO_START=WIKI_MAP_AUTO_START,
            WIKI_MAP_AUTO_END=WIKI_MAP_AUTO_END,
        )

    row = f"- [[wiki/{topic}/README|{topic}]] — processed `{source_filename}`"
    if WIKI_MAP_AUTO_END in text:
        text = text.replace(WIKI_MAP_AUTO_END, f"{row}\n{WIKI_MAP_AUTO_END}")
    else:
        text += f"\n{row}\n"

    _atomic_write_text(map_path, text)


def _atomic_write_text(path: Path, text: str) -> None:
    """Write `text` to `path` atomically via temp-file + `os.replace`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise