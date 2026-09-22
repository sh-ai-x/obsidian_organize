"""Implement `obsidian-organize:add_wiki` deterministically."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .frontmatter import parse_frontmatter, serialize_frontmatter, FrontmatterDict
from .paths import (
    HierarchicalPaths,
    detect_wiki_domain,
    resolve_hierarchical_paths,
    resolve_leaf_path,
    resolve_log_path,
    resolve_staged_path,
    BACKLINK_MARKER_TEMPLATE,
)
from .slug import (
    normalize_topic_slug,
    section_title_to_slug,
    validate_topic_slug,
)
from .wiki_map import append_wiki_map_row


_HIERARCHICAL_AUTO_THRESHOLD = 5

# Match both H2 `## §N Title` and H3 `### N. Title` numbered sections.
# Sources / Notes H2 headings (no number) are intentionally not matched;
# they mark the end of the body content.
_H2_SECTION_RE = re.compile(r"^## §(\d+)\s+(.+?)\s*$")
_H3_SECTION_RE = re.compile(r"^### (\d+)\.\s+(.+?)\s*$")
# Recognized terminator headings (case-insensitive; H2 only).
_END_HEADING_RE = re.compile(r"^##\s+(Sources|Notes)\s*$")


@dataclass
class AddWikiResult:
    topic_path: Path
    staged_path: Path
    topic: str
    topic_frontmatter: FrontmatterDict
    back_links_added: list[Path] = field(default_factory=list)
    # Hierarchical-mode fields. Empty / None for flat mode.
    leaf_paths: list[Path] = field(default_factory=list)
    sub_hub_path: Path | None = None
    major_hub_path: Path | None = None
    # The domain the leaf landed in (or was passed in). Exposed so the
    # caller can log / audit without re-deriving it.
    domain: str | None = None


def promote(
    vault_root: Path,
    topic: str,
    *,
    force: bool = False,
    add_backlinks: bool = True,
    now: datetime | None = None,
    hierarchical: bool = False,
    no_hierarchical: bool = False,
    major: str | None = None,
    domain: str | None = None,
) -> AddWikiResult:
    """Promote the staged research file into a leaf note.

    In **flat mode** (the default), the leaf lands at
    ``wiki/<domain>/<slug>.md``. In **hierarchical mode** (explicit
    ``hierarchical=True`` or a staged research with ≥
    :data:`_HIERARCHICAL_AUTO_THRESHOLD` numbered sections), the staged
    research is split into one leaf note per section under
    ``wiki/<domain>/<slug>/<section>.md`` with auto-generated sub- and
    major-hub files. Pass ``no_hierarchical=True`` to force flat output
    even for large research files.

    The ``domain`` argument auto-detects when not given (see
    :func:`detect_wiki_domain`); callers with multiple wikis should
    pass it explicitly. Every successful promotion also appends a row
    to the vault root ``wiki-map.md`` and an entry to the domain
    ``log.md`` — both updates are idempotent.
    """
    topic_slug = normalize_topic_slug(topic)
    validate_topic_slug(topic_slug)
    staged = resolve_staged_path(vault_root, topic_slug)
    if not staged.exists():
        raise FileNotFoundError(
            f"no staged research at {staged}; run research first"
        )

    staged_text = staged.read_text(encoding="utf-8")
    staged_fm, _ = parse_frontmatter(staged_text)

    sections = _parse_sections(staged_text)
    auto_hierarchical = (
        not no_hierarchical
        and not hierarchical
        and len(sections) >= _HIERARCHICAL_AUTO_THRESHOLD
    )
    use_hierarchical = hierarchical or auto_hierarchical

    resolved_domain = domain or detect_wiki_domain(vault_root)

    if use_hierarchical:
        if not sections:
            raise ValueError(
                f"no parseable sections in {staged}; "
                f"hierarchical mode needs H2 `## §N` or H3 `### N.` headings. "
                f"Pass no_hierarchical=True to force flat output."
            )
        result = _promote_hierarchical(
            vault_root,
            topic_slug,
            staged,
            staged_fm,
            sections,
            domain=resolved_domain,
            major=major,
            force=force,
            now=now,
        )
    else:
        result = _promote_flat(
            vault_root,
            topic_slug,
            staged,
            staged_text,
            staged_fm,
            domain=resolved_domain,
            force=force,
            add_backlinks=add_backlinks,
            now=now,
        )

    result.domain = resolved_domain
    return result


def _promote_flat(
    vault_root: Path,
    topic_slug: str,
    staged: Path,
    staged_text: str,
    staged_fm: FrontmatterDict,
    *,
    domain: str,
    force: bool,
    add_backlinks: bool,
    now: datetime | None,
) -> AddWikiResult:
    """Flat-mode promotion. Writes ``wiki/<domain>/<slug>.md`` plus the
    root ``wiki-map.md`` row and a ``log.md`` entry. The wiki-map /
    log updates are the only side effects that touch files outside the
    new leaf; everything else stays inside ``wiki/<domain>/``."""
    target = resolve_leaf_path(vault_root, domain, topic_slug)
    if target.exists() and not force:
        raise FileExistsError(
            f"leaf note already exists: {target}; pass force=True to overwrite"
        )

    when = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    topic_fm: FrontmatterDict = {
        "topic": topic_slug,
        "domain": domain,
        "created": when,
        "updated": when,
        "tags": _leaf_tags_for_flat(topic_slug),
        "sources": list(staged_fm.get("sources") or []),
        "status": "active",
    }
    body = _render_body(staged_fm, topic_slug)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(serialize_frontmatter(topic_fm, body), encoding="utf-8")

    back_links_added: list[Path] = []
    if add_backlinks:
        marker = BACKLINK_MARKER_TEMPLATE.format(
            domain=domain, topic=topic_slug, timestamp=when
        )
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

    # Side effects: root wiki-map + domain log.
    _append_wiki_map_row(
        vault_root,
        domain=domain,
        note_rel_path=str(target.relative_to(vault_root)),
        title=_title_for(topic_slug),
        summary=staged_fm.get("summary") or f"Distilled from research on {topic_slug}.",
    )
    _append_domain_log(
        vault_root,
        domain=domain,
        when=when,
        note_rel_path=str(target.relative_to(vault_root)),
        title=_title_for(topic_slug),
        summary=staged_fm.get("summary") or "Distilled from staged research.",
    )

    return AddWikiResult(
        topic_path=target,
        staged_path=staged,
        topic=topic_slug,
        topic_frontmatter=topic_fm,
        back_links_added=back_links_added,
    )


def _promote_hierarchical(
    vault_root: Path,
    topic_slug: str,
    staged: Path,
    staged_fm: FrontmatterDict,
    sections: list[tuple[int, str, str]],
    *,
    domain: str,
    major: str | None,
    force: bool,
    now: datetime | None,
) -> AddWikiResult:
    """Hierarchical mode: per-section leaves + auto-generated sub- and major-hubs."""
    paths = resolve_hierarchical_paths(
        vault_root, topic_slug, domain=domain, major=major
    )

    if not force and (paths.sub_hub.exists() or any(
        (paths.leaf_dir / f"{section_title_to_slug(t, sec_num=n)}.md").exists()
        for n, t, _ in sections
    )):
        raise FileExistsError(
            f"hierarchical destination already exists: {paths.slug_dir}; "
            f"pass force=True to overwrite"
        )

    paths.slug_dir.mkdir(parents=True, exist_ok=True)

    when = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    sources = list(staged_fm.get("sources") or [])

    leaf_paths: list[Path] = []
    leaf_entries: list[tuple[str, str, str]] = []  # (slug, title, body) for the hub

    for sec_num, sec_title, sec_body in sections:
        sec_slug = section_title_to_slug(sec_title, sec_num=sec_num)
        leaf_path = paths.leaf_dir / f"{sec_slug}.md"
        leaf_fm: FrontmatterDict = {
            "topic": topic_slug,
            "section": sec_num,
            "title": sec_title,
            "created": when,
            "updated": when,
            "tags": _leaf_tags(topic_slug, sec_title, sec_body),
            "related": _leaf_related(paths, topic_slug, major),
            "status": "active",
        }
        if sources:
            leaf_fm["sources"] = list(sources)
        leaf_body = _render_leaf_body(sec_title, sec_body, paths, topic_slug, major)
        leaf_path.write_text(serialize_frontmatter(leaf_fm, leaf_body), encoding="utf-8")
        leaf_paths.append(leaf_path)
        leaf_entries.append((sec_slug, sec_title, sec_body))

    sub_hub_fm: FrontmatterDict = {
        "topic": topic_slug,
        "title": f"{topic_slug.replace('-', ' ').title()} — leaf-note index",
        "created": when,
        "updated": when,
        "tags": _sub_hub_tags(topic_slug, major),
        "related": _sub_hub_related(paths, topic_slug, major, domain),
        "status": "active",
    }
    sub_hub_body = _render_sub_hub_body(
        topic_slug, paths, major, leaf_entries, staged, sources
    )
    paths.sub_hub.write_text(
        serialize_frontmatter(sub_hub_fm, sub_hub_body), encoding="utf-8"
    )

    major_hub_path: Path | None = None
    if paths.major_hub is not None:
        major_hub_path = paths.major_hub
        major_fm: FrontmatterDict = {
            "topic": major or "root",
            "title": (major or "Root").replace("-", " ").title(),
            "created": when,
            "updated": when,
            "tags": _major_hub_tags(major),
            "related": _major_hub_related(major, domain),
            "status": "active",
        }
        major_body = _render_major_hub_body(major, paths, topic_slug, staged, sources, domain)
        # Only write the major hub if a different staged file hasn't already
        # produced one. Caller may be promoting the second sibling — the
        # existing major hub should be preserved, not overwritten.
        if not major_hub_path.exists() or force:
            major_hub_path.write_text(
                serialize_frontmatter(major_fm, major_body), encoding="utf-8"
            )

    # Mark staged file as promoted, pointing at the sub-hub.
    staged_fm["status"] = "promoted"
    staged_fm["updated"] = when
    staged_fm["promoted_to"] = str(paths.sub_hub.relative_to(vault_root))
    staged_text = staged.read_text(encoding="utf-8")
    staged.write_text(
        serialize_frontmatter(staged_fm, _body_after_parse(staged_text)),
        encoding="utf-8",
    )

    # Side effects: root wiki-map (sub-hub is the durable entry point,
    # not the per-section leaves) + domain log.
    leaf_count = len(leaf_paths)
    major_label = f"{major}/" if major else ""
    sub_hub_title = f"{topic_slug.replace('-', ' ').title()} — sub-hub"
    summary = (
        f"Hierarchical promotion: {leaf_count} leaf notes under "
        f"{major_label}{topic_slug}/_index."
    )
    _append_wiki_map_row(
        vault_root,
        domain=domain,
        note_rel_path=str(paths.sub_hub.relative_to(vault_root)),
        title=sub_hub_title,
        summary=summary,
    )
    _append_domain_log(
        vault_root,
        domain=domain,
        when=when,
        note_rel_path=str(paths.sub_hub.relative_to(vault_root)),
        title=sub_hub_title,
        summary=f"{leaf_count} leaf notes" + (f" (major: {major})" if major else ""),
    )

    return AddWikiResult(
        topic_path=paths.sub_hub,
        staged_path=staged,
        topic=topic_slug,
        topic_frontmatter=staged_fm,
        leaf_paths=leaf_paths,
        sub_hub_path=paths.sub_hub,
        major_hub_path=major_hub_path,
    )


def _parse_sections(text: str) -> list[tuple[int, str, str]]:
    """Parse a staged-research body into ``(num, title, body)`` tuples.

    H2 sections matching ``## §N Title`` and H3 sections matching
    ``### N. Title`` are both recognized. The parser stops accumulating
    at an ``## Sources`` or ``## Notes`` H2 heading (the staged-file
    terminators) so the Sources/Notes tail is never treated as a
    leaf-note section.
    """
    _, body = parse_frontmatter(text)
    out: list[tuple[int, str, str]] = []
    current_num: int | None = None
    current_title: str | None = None
    current_body: list[str] = []

    def _flush() -> None:
        if current_num is not None and current_title is not None:
            out.append((current_num, current_title, "\n".join(current_body).strip()))

    for line in body.split("\n"):
        m_h2 = _H2_SECTION_RE.match(line)
        m_h3 = _H3_SECTION_RE.match(line)
        if m_h2:
            _flush()
            current_num = int(m_h2.group(1))
            current_title = m_h2.group(2).strip()
            current_body = []
            continue
        if m_h3:
            _flush()
            current_num = int(m_h3.group(1))
            current_title = m_h3.group(2).strip()
            current_body = []
            continue
        if _END_HEADING_RE.match(line):
            _flush()
            current_num = None
            current_title = None
            current_body = []
            continue
        if current_num is not None:
            current_body.append(line)

    _flush()
    return out


def _leaf_tags(topic_slug: str, sec_title: str, sec_body: str) -> list[str]:
    """Pick 3-7 flat tags for a leaf note. The topic slug is always included
    so cross-leaf graph edges exist within the same hub."""
    pool = [
        topic_slug,
        *re.findall(r"\b[a-z][a-z0-9-]{2,30}\b", sec_title.lower()),
        *re.findall(r"\b[a-z][a-z0-9-]{2,30}\b", sec_body.lower()[:1500]),
    ]
    seen: set[str] = set()
    out: list[str] = []
    for tag in pool:
        if tag in seen:
            continue
        seen.add(tag)
        out.append(tag)
        if len(out) >= 7:
            break
    if len(out) < 3:
        out.append("ai-security")
    return out[:7]


def _leaf_related(
    paths: HierarchicalPaths, topic_slug: str, major: str | None
) -> list[str]:
    """Build the ``related:`` list for a leaf note — vault-relative wikilinks."""
    related: list[str] = [f"{topic_slug}/_index"]
    if major:
        related.append(f"{major}/_index")
    return related


def _sub_hub_tags(topic_slug: str, major: str | None) -> list[str]:
    tags = [topic_slug]
    if major:
        tags.append(major)
    tags.append("sub-hub")
    return tags[:7]


def _sub_hub_related(
    paths: HierarchicalPaths, topic_slug: str, major: str | None, domain: str
) -> list[str]:
    related: list[str] = []
    if major:
        related.append(f"{major}/_index")
    related.append(f"{domain}/00-index")
    return related


def _major_hub_tags(major: str | None) -> list[str]:
    if not major:
        return ["hub"]
    return [major, "hub"]


def _major_hub_related(major: str | None, domain: str) -> list[str]:
    return [f"{domain}/00-index"]


def _render_leaf_body(
    title: str,
    body: str,
    paths: HierarchicalPaths,
    topic_slug: str,
    major: str | None,
) -> str:
    """Render the body of a single leaf note: H1 + TL;DR + body + Related."""
    tldr = _first_sentence(body) or title
    out: list[str] = [f"# {title}", ""]
    out.append(f"> {tldr}")
    out.append("")
    if body.strip():
        out.append(body.strip())
        out.append("")
    out.append("## Related")
    out.append("")
    out.append(f"- [[{topic_slug}/_index|{topic_slug} sub-hub]]")
    if major:
        out.append(f"- [[{major}/_index|{major} hub]]")
    out.append("")
    return "\n".join(out)


def _render_sub_hub_body(
    topic_slug: str,
    paths: HierarchicalPaths,
    major: str | None,
    leaf_entries: list[tuple[str, str, str]],
    staged: Path,
    sources: list[str],
) -> str:
    title = topic_slug.replace("-", " ").title()
    out: list[str] = [f"# {title}", ""]
    out.append(
        f"> Leaf-note index for **{topic_slug}** — {len(leaf_entries)} per-section notes distilled from the staged research below."
    )
    out.append("")
    out.append("## Leaf Notes")
    out.append("")
    for slug, sec_title, _ in leaf_entries:
        out.append(f"- [[{slug}|{sec_title}]]")
    out.append("")
    out.append("## Source")
    out.append("")
    # The staged research lives at <vault_root>/_research/<topic_slug>.md
    # (see resolve_staged_path). Render the link with that vault-relative
    # path; the leaf note and the staged file share the vault root so the
    # wikilink resolves from anywhere under it.
    staged_vault_rel = f"_research/{topic_slug}.md"
    out.append(f"Full research dossier: [[{staged_vault_rel}]]")
    out.append("")
    if sources:
        out.append("## Sources")
        out.append("")
        for src in sources:
            out.append(f"- {src}")
        out.append("")
    out.append("## Related")
    out.append("")
    if major:
        out.append(f"- [[{major}/_index|{major} hub]] — parent major-hub")
    out.append("- [[00-index|00-index]] — domain master index")
    out.append("")
    return "\n".join(out)


def _render_major_hub_body(
    major: str | None,
    paths: HierarchicalPaths,
    topic_slug: str,
    staged: Path,
    sources: list[str],
    domain: str,
) -> str:
    title = (major or "Root").replace("-", " ").title()
    out: list[str] = [f"# {title}", ""]
    out.append(
        f"> Major-hub for the **{major}** sub-tree — links each per-topic sub-hub."
    )
    out.append("")
    out.append("## Sub-Domains")
    out.append("")
    out.append(f"- [[{topic_slug}/_index|{topic_slug} sub-hub]] — first promoted sub-domain")
    out.append("")
    out.append("## Source Research")
    out.append("")
    out.append(f"- [[_research/{topic_slug}.md|staged research dossier]]")
    out.append("")
    out.append("## Related")
    out.append("")
    out.append(f"- [[00-index|{domain} index]] — domain master")
    out.append("")
    return "\n".join(out)


def _first_sentence(text: str) -> str:
    """Return the first non-heading, non-table, non-blockquote sentence."""
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if s.startswith(("#", "|", ">", "-", "*", "```")):
            continue
        # Truncate to a single sentence
        for terminator in (". ", "! ", "? "):
            if terminator in s:
                return s.split(terminator, 1)[0] + terminator.strip()
        return s[:240]
    return ""


def _render_body(staged_fm: FrontmatterDict, topic_slug: str) -> str:
    sources = staged_fm.get("sources") or []
    summary = staged_fm.get("summary") or "(auto-generated from staged Notes)"
    title = topic_slug.replace("-", " ").title()
    out: list[str] = [f"# {title}", "", f"> {summary}", "", "## Summary", ""]
    out.append(summary)
    out.append("")
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


def _title_for(topic_slug: str) -> str:
    """Human-readable title from a topic slug. ``jwt-pitfalls`` → ``JWT Pitfalls``."""
    return topic_slug.replace("-", " ").title()


def _leaf_tags_for_flat(topic_slug: str) -> list[str]:
    """Flat-mode tag list. Includes the slug so cross-leaf graph edges
    exist within the same wiki-domain."""
    return [topic_slug]


def _append_wiki_map_row(
    vault_root: Path,
    *,
    domain: str,
    note_rel_path: str,
    title: str,
    summary: str,
) -> None:
    """Thin wrapper around :func:`append_wiki_map_row` kept here so
    callers of :func:`promote` do not need to know about the ``_lib``
    sub-package layout. Idempotent."""
    append_wiki_map_row(
        vault_root,
        domain=domain,
        note_rel_path=note_rel_path,
        title=title,
        summary=summary,
    )


def _append_domain_log(
    vault_root: Path,
    *,
    domain: str,
    when: str,
    note_rel_path: str,
    title: str,
    summary: str,
) -> None:
    """Append one log entry to ``<vault>/wiki/<domain>/log.md``.

    Idempotent in the sense that re-running for the same promotion only
    appends a single duplicate line; the file is never rewritten. The
    caller is responsible for ensuring a single append per logical
    promotion.
    """
    log = resolve_log_path(vault_root, domain)
    log.parent.mkdir(parents=True, exist_ok=True)
    if not log.exists():
        header = f"# {domain.replace('-', ' ').title()} — Change Log\n\n"
        log.write_text(header, encoding="utf-8")
    date = when.split("T", 1)[0]
    entry = (
        f"## [{date}] ingest | {title}\n"
        f"{summary} — [[{note_rel_path}|{title}]]\n\n"
    )
    with log.open("a", encoding="utf-8") as f:
        f.write(entry)

