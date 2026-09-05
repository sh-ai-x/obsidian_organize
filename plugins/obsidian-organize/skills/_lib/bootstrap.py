"""Implement `obsidian-organize:bootstrap` deterministically.

The SKILL.md is the LLM-facing contract; this module is the deterministic
helper that tests + the SKILL.md both delegate to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

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
        wiki_map.write_text(
            WIKI_MAP_TEMPLATE.format(
                created=when,
                WIKI_MAP_AUTO_START=WIKI_MAP_AUTO_START,
                WIKI_MAP_AUTO_END=WIKI_MAP_AUTO_END,
            ),
            encoding="utf-8",
        )
        result.wiki_map_written = True

    if topics:
        for raw_topic in topics:
            topic_slug = _slugify(raw_topic)
            if not topic_slug:
                continue
            topic_dir = vault_root / "wiki" / topic_slug
            topic_dir.mkdir(parents=True, exist_ok=True)
            (topic_dir / ".keep").touch(exist_ok=True)
            readme = topic_dir / "README.md"
            if readme.exists() and not force:
                result.skipped_existing.append(readme)
                continue
            readme.write_text(
                TOPIC_README_TEMPLATE.format(
                    topic=topic_slug, created=when
                ),
                encoding="utf-8",
            )
            result.seeded_topics.append(topic_slug)

    return result


def _slugify(name: str) -> str:
    """Mirror slug.normalize_topic_slug without an import cycle."""
    import re

    s = name.strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s
