"""Implement `obsidian-organize:add_wiki` deterministically."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .frontmatter import parse_frontmatter, serialize_frontmatter, FrontmatterDict
from .paths import resolve_staged_path, resolve_topic_path, BACKLINK_MARKER_TEMPLATE
from .slug import normalize_topic_slug, validate_topic_slug


@dataclass
class AddWikiResult:
    topic_path: Path
    staged_path: Path
    topic: str
    topic_frontmatter: FrontmatterDict
    back_links_added: list[Path] = field(default_factory=list)


def promote(
    vault_root: Path,
    topic: str,
    *,
    force: bool = False,
    add_backlinks: bool = True,
    now: datetime | None = None,
) -> AddWikiResult:
    """Promote the staged research file into a topic note."""
    topic_slug = normalize_topic_slug(topic)
    validate_topic_slug(topic_slug)
    staged = resolve_staged_path(vault_root, topic_slug)
    if not staged.exists():
        raise FileNotFoundError(
            f"no staged research at {staged}; run research first"
        )

    target = resolve_topic_path(vault_root, topic_slug)
    if target.exists() and not force:
        raise FileExistsError(
            f"topic note already exists: {target}; pass force=True to overwrite"
        )

    staged_text = staged.read_text(encoding="utf-8")
    staged_fm, _ = parse_frontmatter(staged_text)

    when = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    topic_fm: FrontmatterDict = {
        "topic": topic_slug,
        "created": when,
        "updated": when,
        "tags": [f"topic/{topic_slug}"],
        "sources": list(staged_fm.get("sources") or []),
        "status": "active",
    }
    body = _render_body(staged_fm)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(serialize_frontmatter(topic_fm, body), encoding="utf-8")

    back_links_added: list[Path] = []
    if add_backlinks:
        marker = BACKLINK_MARKER_TEMPLATE.format(topic=topic_slug, timestamp=when)
        for src in topic_fm["sources"]:
            src_path = _resolve_source(vault_root, src)
            if src_path is None or not src_path.exists():
                continue
            existing = src_path.read_text(encoding="utf-8")
            new = existing.rstrip() + "\n" + marker + "\n"
            src_path.write_text(new, encoding="utf-8")
            back_links_added.append(src_path)

    # Mark staged file as promoted.
    staged_fm["status"] = "promoted"
    staged_fm["updated"] = when
    staged_fm["promoted_to"] = str(target.relative_to(vault_root))
    staged.write_text(
        serialize_frontmatter(staged_fm, _body_after_parse(staged_text)),
        encoding="utf-8",
    )

    return AddWikiResult(
        topic_path=target,
        staged_path=staged,
        topic=topic_slug,
        topic_frontmatter=topic_fm,
        back_links_added=back_links_added,
    )


def _render_body(staged_fm: FrontmatterDict) -> str:
    sources = staged_fm.get("sources") or []
    out: list[str] = ["## Summary", "", "(auto-generated from staged Notes)", ""]
    out.append("## Sources")
    out.append("")
    if not sources:
        out.append("_(no sources)_")
    else:
        for src in sources:
            out.append(f"- {src}")
    out.append("")
    out.append("## Related")
    out.append("")
    out.append("_(detected wikilinks go here)_")
    out.append("")
    return "\n".join(out)


def _resolve_source(vault_root: Path, src: str) -> Path | None:
    """A source may be a URL, an absolute path, or a vault-relative path."""
    if src.startswith(("http://", "https://")):
        return None
    p = Path(src).expanduser()
    if p.is_absolute():
        return p
    return vault_root / src


def _body_after_parse(text: str) -> str:
    _, body = parse_frontmatter(text)
    return body
