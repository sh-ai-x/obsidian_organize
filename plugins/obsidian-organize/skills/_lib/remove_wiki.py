"""Implement `obsidian-organize:remove_wiki` deterministically."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .frontmatter import parse_frontmatter, serialize_frontmatter, FrontmatterDict
from .paths import (
    resolve_archive_path,
    resolve_staged_path,
    resolve_topic_path,
    scan_backlinks,
)
from .slug import normalize_topic_slug, validate_topic_slug


@dataclass
class RemoveWikiResult:
    topic: str
    archived_from: Path | None
    archived_to: Path | None
    source_edits: list[Path] = field(default_factory=list)
    topic_note_deleted: bool = False
    dry_run: bool = False


def retire(
    vault_root: Path,
    topic: str,
    *,
    dry_run: bool = False,
    keep_staged: bool = False,
    now: datetime | None = None,
) -> RemoveWikiResult:
    """Retire a topic: archive the staged file, edit source back-links, delete topic note."""
    topic_slug = normalize_topic_slug(topic)
    validate_topic_slug(topic_slug)
    when = now or datetime.now(timezone.utc)

    topic_path = resolve_topic_path(vault_root, topic_slug)
    staged = resolve_staged_path(vault_root, topic_slug)
    archive = resolve_archive_path(vault_root, topic_slug, now=when)

    if not topic_path.exists():
        raise FileNotFoundError(f"no active topic at {topic_path}; nothing to remove")

    hits = scan_backlinks(vault_root, topic_slug)
    source_edits = sorted({h.file for h in hits})

    if dry_run:
        return RemoveWikiResult(
            topic=topic_slug,
            archived_from=staged if staged.exists() else None,
            archived_to=archive if staged.exists() else None,
            source_edits=source_edits,
            topic_note_deleted=True,
            dry_run=True,
        )

    # 1. Update topic note frontmatter to retired, then delete.
    topic_text = topic_path.read_text(encoding="utf-8")
    topic_fm, _ = parse_frontmatter(topic_text)
    topic_fm["status"] = "retired"
    topic_fm["retired_at"] = when.isoformat(timespec="seconds")
    # Note: we don't write retired_to yet because archive path depends on
    # whether the staged file existed. Update after step 2.

    # 2. Move staged → archive (or just mark archived if keep_staged).
    archived_from: Path | None = None
    archived_to: Path | None = None
    if staged.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        staged_text = staged.read_text(encoding="utf-8")
        staged_fm, staged_body = parse_frontmatter(staged_text)
        staged_fm["status"] = "archived"
        staged_fm["updated"] = when.isoformat(timespec="seconds")
        if keep_staged:
            staged.write_text(
                serialize_frontmatter(staged_fm, staged_body), encoding="utf-8"
            )
            archived_from = staged
            archived_to = staged
        else:
            archive.write_text(
                serialize_frontmatter(staged_fm, staged_body), encoding="utf-8"
            )
            staged.unlink()
            archived_from = staged
            archived_to = archive
        topic_fm["retired_to"] = str(
            (archived_to).relative_to(vault_root)
        )

    # 3. Strip back-link lines from each source file.
    for src in source_edits:
        text = src.read_text(encoding="utf-8")
        lines = text.splitlines()
        marker = f"[[topics/{topic_slug}]]"
        new_lines = [
            line for line in lines
            if not (marker in line and line.lstrip().startswith("<!--"))
        ]
        if len(new_lines) != len(lines):
            src.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    # 4. Honor the keep_staged semantics by leaving the topic-note metadata
    #    in place if the user asked to keep staged in-place. We always delete
    #    the topic note after archiving, per SKILL.md.
    topic_path.unlink()

    return RemoveWikiResult(
        topic=topic_slug,
        archived_from=archived_from,
        archived_to=archived_to,
        source_edits=source_edits,
        topic_note_deleted=True,
        dry_run=False,
    )
