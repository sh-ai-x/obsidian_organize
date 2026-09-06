"""Implement `obsidian-organize:research` deterministically.

The SKILL.md is the LLM-facing contract; this module is the deterministic
helper that tests + the SKILL.md both delegate to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .frontmatter import serialize_frontmatter, FrontmatterDict
from .io import atomic_write_text
from .paths import resolve_staged_path
from .slug import normalize_topic_slug, validate_topic_slug


@dataclass
class ResearchInput:
    topic: str
    sources: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class ResearchResult:
    staged_path: Path
    topic: str
    frontmatter: FrontmatterDict


def write_staged_file(
    vault_root: Path,
    input: ResearchInput,
    *,
    now: datetime | None = None,
    append: bool = False,
) -> ResearchResult:
    """Write or append the staged research file. Returns the resolved path + fm."""
    topic = normalize_topic_slug(input.topic)
    validate_topic_slug(topic)
    path = resolve_staged_path(vault_root, topic)

    if path.exists() and not append:
        raise FileExistsError(
            f"staged file already exists: {path}; pass append=True to extend"
        )

    when = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")

    if append and path.exists():
        from .frontmatter import parse_frontmatter  # local import to avoid cycle
        existing_text = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(existing_text)
        fm["updated"] = when
        existing_sources = list(fm.get("sources", []))
        for src in input.sources:
            if src not in existing_sources:
                existing_sources.append(src)
        fm["sources"] = existing_sources
        new_body = body.rstrip() + "\n\n## Appended " + when + "\n\n"
        for note in input.notes:
            new_body += f"> {note}\n"
        atomic_write_text(path, serialize_frontmatter(fm, new_body))
        return ResearchResult(staged_path=path, topic=topic, frontmatter=fm)

    path.parent.mkdir(parents=True, exist_ok=True)
    fm: FrontmatterDict = {
        "topic": topic,
        "created": when,
        "sources": list(input.sources),
        "status": "staged",
    }
    body = _render_body(input.sources, input.notes)
    atomic_write_text(path, serialize_frontmatter(fm, body))
    return ResearchResult(staged_path=path, topic=topic, frontmatter=fm)


def _render_body(sources: list[str], notes: list[str]) -> str:
    out: list[str] = ["## Sources", ""]
    if not sources:
        out.append("_(no sources yet)_")
    else:
        for src in sources:
            out.append(f"- {src}")
    out.append("")
    out.append("## Notes")
    out.append("")
    if not notes:
        out.append("_add quotes here_")
    else:
        for note in notes:
            out.append(f"> {note}")
    out.append("")
    return "\n".join(out)
