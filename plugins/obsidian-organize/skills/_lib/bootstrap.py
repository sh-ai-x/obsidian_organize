"""Implement `obsidian-organize:bootstrap` deterministically.

The SKILL.md is the LLM-facing contract; this module is the deterministic
helper that tests + the SKILL.md both delegate to.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .io import atomic_write_text
from .paths import safe_filename
from .slug import normalize_topic_slug

# fcntl is POSIX-only. Guard the import so a Windows / non-POSIX
# platform degrades gracefully (still appends, but without the
# cross-process lock) rather than failing at import time.
try:
    import fcntl  # type: ignore[import-not-found]
    _HAS_FCNTL = True
except ImportError:  # pragma: no cover - non-POSIX platforms
    fcntl = None  # type: ignore[assignment]
    _HAS_FCNTL = False

logger = logging.getLogger(__name__)

WIKI_MAP_AUTO_START = "<!-- obsidian-organize:wiki-map:auto-start -->"
WIKI_MAP_AUTO_END = "<!-- obsidian-organize:wiki-map:auto-end -->"

WIKI_MAP_TEMPLATE = """---
type: wiki-map
created: {created}
---

# Wiki Map

{WIKI_MAP_AUTO_START}
<!-- Each row below is appended by obsidian-organize:add_wiki when a new topic lands. -->
<!-- Do not edit by hand; re-running `bootstrap --force --topics ...` re-seeds. -->

## Topics

{WIKI_MAP_AUTO_END}
"""

TOPIC_README_TEMPLATE = """---
topic: {topic}
seeded-by: bootstrap
created: {created}
---

# {topic}

Topic directory seeded by `obsidian-organize:bootstrap --topics`.
The first call to `obsidian-organize:add_wiki {topic}` replaces this file
with the promoted topic note (frontmatter `status: active`, body populated
from `_research/{topic}.md`).
"""


@dataclass
class BootstrapResult:
    vault_root: Path
    created: list[Path] = field(default_factory=list)
    skipped_existing: list[Path] = field(default_factory=list)
    seeded_topics: list[str] = field(default_factory=list)
    wiki_map_written: bool = False


def bootstrap(
    vault_root: Path,
    *,
    force: bool = False,
    topics: list[str] | None = None,
    now: datetime | None = None,
) -> BootstrapResult:
    """Create the canonical topic-organizer layout under `vault_root`.

    Refuses to clobber existing files unless `force=True`.
    """
    vault_root = vault_root.expanduser().resolve()
    when = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")

    result = BootstrapResult(vault_root=vault_root)

    target_dirs = [
        vault_root / "Clippings",
        vault_root / "Clippings" / "processed",
        vault_root / "wiki",
        vault_root / "_research",
        vault_root / "_archive" / "research",
        vault_root / "topics",
    ]
    for d in target_dirs:
        if d.exists() and any(d.iterdir()) and not force:
            result.skipped_existing.append(d)
            continue
        d.mkdir(parents=True, exist_ok=True)
        keep = d / ".keep"
        keep.touch(exist_ok=True)
        result.created.append(d)

    wiki_map = vault_root / "wiki-map.md"
    if wiki_map.exists() and not force:
        result.skipped_existing.append(wiki_map)
    else:
        atomic_write_text(
            wiki_map,
            WIKI_MAP_TEMPLATE.format(
                created=when,
                WIKI_MAP_AUTO_START=WIKI_MAP_AUTO_START,
                WIKI_MAP_AUTO_END=WIKI_MAP_AUTO_END,
            ),
        )
        result.wiki_map_written = True

    if topics:
        for raw_topic in topics:
            topic_slug = normalize_topic_slug(raw_topic)
            if not topic_slug:
                continue
            topic_dir = vault_root / "wiki" / topic_slug
            topic_dir.mkdir(parents=True, exist_ok=True)
            (topic_dir / ".keep").touch(exist_ok=True)
            readme = topic_dir / "README.md"
            if readme.exists() and not force:
                result.skipped_existing.append(readme)
                continue
            atomic_write_text(
                readme,
                TOPIC_README_TEMPLATE.format(
                    topic=topic_slug, created=when
                ),
            )
            result.seeded_topics.append(topic_slug)

    return result


# --------------------------------------------------------------------------- #
# Wiki-map row append (single source of truth for seed-and-append)
# --------------------------------------------------------------------------- #


def append_wiki_map_row(
    vault_root: Path,
    topic: str,
    source_filename: str,
    *,
    now: datetime | None = None,
) -> bool:
    """Append one row to `wiki-map.md`, seeding the file from
    `WIKI_MAP_TEMPLATE` first if it doesn't exist.

    Returns `True` if a row was appended, `False` if an identical row
    already exists (idempotent — re-running after a partial failure
    must not duplicate rows).

    Centralised here so `process_clippings` and any future caller share
    the same seed template, idempotency rule, and atomic-write contract.
    The `now` parameter threads the caller's timestamp through to the
    `created:` field when we seed the file for the first time; on
    subsequent appends the existing `created:` is preserved (the file
    already exists, we only add rows).

    The write is atomic (temp file + `os.replace`) so a crash or SIGKILL
    mid-write can never leave `wiki-map.md` truncated or corrupted.

    A `fcntl.flock(LOCK_EX)` lock guards the entire read-modify-write
    so concurrent invocations do not both read the same snapshot and
    clobber each other (lost-update / TOCTOU). The lock is held on a
    sibling file `wiki-map.md.lock` — locking `wiki-map.md` itself
    would be unsafe because `atomic_write_text` swaps the inode out
    from under the lock via `os.replace`. The lock file is opened
    O_CREAT so the first writer creates it; subsequent writers just
    take the lock.
    """
    map_path = vault_root / "wiki-map.md"
    lock_path = map_path.with_name(map_path.name + ".lock")
    when = now or datetime.now(timezone.utc)
    when_iso = when.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _do_append() -> bool:
        if map_path.exists():
            text = map_path.read_text(encoding="utf-8")
        else:
            text = WIKI_MAP_TEMPLATE.format(
                created=when_iso,
                WIKI_MAP_AUTO_START=WIKI_MAP_AUTO_START,
                WIKI_MAP_AUTO_END=WIKI_MAP_AUTO_END,
            )

        row = f"- [[wiki/{topic}/README|{topic}]] — processed `{safe_filename(source_filename)}`"

        # Idempotency: if the exact row already exists, do nothing. Catches
        # the failure mode where the wiki-map append succeeded but the
        # subsequent `src.rename` failed — re-running would otherwise
        # duplicate the row.
        if row in text:
            logger.info("wiki-map row already present, skipping append: %s", row)
            return False

        if WIKI_MAP_AUTO_END in text:
            text = text.replace(WIKI_MAP_AUTO_END, f"{row}\n{WIKI_MAP_AUTO_END}")
        else:
            text += f"\n{row}\n"

        atomic_write_text(map_path, text)
        return True

    if not _HAS_FCNTL:
        # Non-POSIX platform (e.g. Windows). fcntl is not available;
        # degrade gracefully — still append, but without the
        # cross-process lock. The atomic-write + idempotency check
        # already prevent partial / duplicate writes from a single
        # process; the only thing lost is the cross-process lost-update
        # guarantee, which the import-guard is logging for visibility.
        logger.warning(
            "fcntl not available on this platform; wiki-map appends are not "
            "cross-process locked (path=%s)",
            map_path,
        )
        return _do_append()

    # POSIX: hold an exclusive flock across the whole read-modify-write.
    # Open the lock file with O_CREAT|O_RDWR so the first writer creates
    # it; subsequent writers open the existing inode and take the lock.
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            return _do_append()
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
