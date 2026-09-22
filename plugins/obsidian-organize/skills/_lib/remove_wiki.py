"""Implement `obsidian-organize:remove_wiki` deterministically."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .frontmatter import parse_frontmatter, serialize_frontmatter, FrontmatterDict
from .paths import (
    detect_wiki_domain,
    resolve_archive_path,
    resolve_leaf_path,
    resolve_staged_path,
    resolve_topic_path,
    scan_backlinks,
)
from .slug import normalize_topic_slug, validate_topic_slug
from .wiki_map import remove_wiki_map_row


@dataclass
class RemoveWikiResult:
    topic: str
    archived_from: Path | None
    archived_to: Path | None
    source_edits: list[Path] = field(default_factory=list)
    topic_note_deleted: bool = False
    dry_run: bool = False
    wiki_map_row_removed: bool = False


def retire(
    vault_root: Path,
    topic: str,
    *,
    dry_run: bool = False,
    keep_staged: bool = False,
    now: datetime | None = None,
    domain: str | None = None,
) -> RemoveWikiResult:
    """Retire a topic: archive the staged file, edit source back-links,
    delete the leaf note, and drop the row from ``wiki-map.md``.

    The leaf is looked up at ``wiki/<domain>/<slug>.md`` (the flat-mode
    destination). ``<domain>`` auto-detects when not given (see
    :func:`detect_wiki_domain`); callers with multiple wikis should
    pass it explicitly so the right sub-tree is searched. The legacy
    ``topics/<slug>.md`` path is checked as a fallback so notes
    written by older releases can still be retired.
    """
    topic_slug = normalize_topic_slug(topic)
    validate_topic_slug(topic_slug)
    when = now or datetime.now(timezone.utc)

    resolved_domain = domain or detect_wiki_domain(vault_root)
    leaf_path = resolve_leaf_path(vault_root, resolved_domain, topic_slug)
    legacy_topic_path = resolve_topic_path(vault_root, topic_slug)
    topic_path = leaf_path if leaf_path.exists() else legacy_topic_path
    if not topic_path.exists():
        raise FileNotFoundError(
            f"no active topic at {leaf_path} (or legacy {legacy_topic_path}); "
            f"nothing to remove"
        )

    staged = resolve_staged_path(vault_root, topic_slug)
    archive = resolve_archive_path(vault_root, topic_slug, now=when)

    hits = scan_backlinks(vault_root, topic_slug, domain=resolved_domain)
    source_edits = sorted({h.file for h in hits})
    leaf_rel = str(topic_path.relative_to(vault_root))

    if dry_run:
        return RemoveWikiResult(
            topic=topic_slug,
            archived_from=staged if staged.exists() else None,
            archived_to=archive if staged.exists() else None,
            source_edits=source_edits,
            topic_note_deleted=True,
            dry_run=True,
            wiki_map_row_removed=False,
        )

    # 1. Mark the staged file as archived (then move to archive/ unless
    #    the caller asked to keep it in place).
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

    # 2. Strip back-link marker lines from each source file.
    for src in source_edits:
        text = src.read_text(encoding="utf-8")
        lines = text.splitlines()
        marker = f"[[wiki/{resolved_domain}/{topic_slug}]]"
        new_lines = [
            line for line in lines
            if not (marker in line and line.lstrip().startswith("<!--"))
        ]
        if len(new_lines) != len(lines):
            src.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    # 3. Delete the leaf note itself.
    topic_path.unlink()

    # 4. Drop the wiki-map row (idempotent; safe on missing file).
    remove_wiki_map_row(vault_root, note_rel_path=leaf_rel)

    return RemoveWikiResult(
        topic=topic_slug,
        archived_from=archived_from,
        archived_to=archived_to,
        source_edits=source_edits,
        topic_note_deleted=True,
        dry_run=False,
        wiki_map_row_removed=True,
    )
