"""Deterministic updater for the vault root ``wiki-map.md``.

The root ``wiki-map.md`` is the single entry point for the whole wiki.
``obsidian-organize:add_wiki`` appends a row on every promotion,
``obsidian-organize:remove_wiki`` strips the row when a topic is
retired. Both are idempotent so re-running never duplicates rows.

The file is treated as user-managed content: prior themed sections are
preserved exactly as written. The auto-managed block sits at the bottom
of the file, delimited by ``obsidian-organize:wiki-map:auto-start`` /
``auto-end`` markers and a ``## 🆕 Recent Additions`` heading.
"""

from __future__ import annotations

from pathlib import Path

AUTO_START = "<!-- obsidian-organize:wiki-map:auto-start -->"
AUTO_END = "<!-- obsidian-organize:wiki-map:auto-end -->"
RECENT_SECTION_HEADING = "## 🆕 Recent Additions"

# Header of the auto-managed block. The placeholder {rows} is replaced
# with one bullet per wikilink, in insertion order.
AUTO_BLOCK_TEMPLATE = (
    "\n"
    f"{AUTO_START}\n"
    "<!-- Each row below is appended by obsidian-organize:add_wiki when a new topic lands. -->\n"
    "<!-- Do not edit by hand; re-running add_wiki is idempotent. -->\n"
    "\n"
    f"{RECENT_SECTION_HEADING}\n"
    "\n"
    "{rows}\n"
    f"{AUTO_END}\n"
)


def _row(*, domain: str, note_rel_path: str, title: str, summary: str) -> str:
    """Format a single wiki-map row.

    Format::

        - [[wiki/<domain>/<note>|<Title>]] — <summary> (<domain>)

    The trailing ``(<domain>)`` tag is what makes the row useful at a
    glance — the user's wiki-map is grouped by theme, not by domain, so
    the domain label is the only way to know which sub-tree a fresh row
    belongs to without opening the link.
    """
    return f"- [[{note_rel_path}|{title}]] — {summary} ({domain})"


def append_wiki_map_row(
    vault_root: Path,
    *,
    domain: str,
    note_rel_path: str,
    title: str,
    summary: str,
) -> None:
    """Append a row to ``<vault_root>/wiki-map.md`` (idempotent).

    Behaviour:

    - File missing → create with auto-markers + Recent Additions section.
    - File present with auto-markers → insert into the existing
      Recent Additions section (between markers).
    - File present without auto-markers → append the markers +
      Recent Additions section at the bottom, preserving all prior
      themed content.
    - Re-running for an identical row is a no-op.
    """
    row = _row(
        domain=domain, note_rel_path=note_rel_path, title=title, summary=summary
    )

    wiki_map = vault_root / "wiki-map.md"
    if not wiki_map.exists():
        body = "# Wiki Map\n" + AUTO_BLOCK_TEMPLATE.format(rows=row)
        wiki_map.write_text(body, encoding="utf-8")
        return

    text = wiki_map.read_text(encoding="utf-8")
    if row in text:
        return  # idempotent

    if AUTO_START in text and AUTO_END in text:
        # Insert the row just before the end-marker, inside the section.
        text = text.replace(AUTO_END, f"{row}\n{AUTO_END}")
    else:
        # Append the auto-managed block at the bottom of the existing file.
        block = AUTO_BLOCK_TEMPLATE.format(rows=row)
        text = text.rstrip("\n") + "\n" + block
    wiki_map.write_text(text, encoding="utf-8")


def remove_wiki_map_row(vault_root: Path, *, note_rel_path: str) -> None:
    """Drop a row from ``wiki-map.md`` (idempotent, safe on missing file)."""
    wiki_map = vault_root / "wiki-map.md"
    if not wiki_map.exists():
        return

    text = wiki_map.read_text(encoding="utf-8")
    if note_rel_path not in text:
        return  # idempotent

    lines = text.splitlines()
    keep: list[str] = []
    for line in lines:
        # Match a bullet whose wikilink target is `note_rel_path`. The
        # title segment after the pipe may contain `]` so we anchor on
        # the closing `]]`.
        if line.lstrip().startswith("- [") and note_rel_path in line:
            continue
        keep.append(line)
    wiki_map.write_text("\n".join(keep) + "\n", encoding="utf-8")
