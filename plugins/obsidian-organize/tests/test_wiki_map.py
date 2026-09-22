"""Tests for the wiki-map auto-update contract.

`wiki-map.md` is the root index that `obsidian-organize:add_wiki` updates
on every promotion. The contract is:

- If the file does not exist, create it with auto-markers + a
  `## 🆕 Recent Additions` section.
- If auto-markers exist, insert the row in the section between them.
- If the file exists but has no markers, append the markers + section at
  the bottom (preserving prior content).
- Re-running for the same wikilink must be a no-op.
- Removing a wikilink must drop only that row.
"""

from __future__ import annotations

import re

import pytest

from _lib.wiki_map import (
    RECENT_SECTION_HEADING,
    append_wiki_map_row,
    remove_wiki_map_row,
)


# ---------------------------------------------------------------------------
# append_wiki_map_row
# ---------------------------------------------------------------------------


def test_append_creates_file_when_missing(tmp_path):
    append_wiki_map_row(
        tmp_path,
        domain="ai-agent-wiki",
        note_rel_path="wiki/ai-agent-wiki/jwt-pitfalls.md",
        title="JWT Pitfalls",
        summary="Common JWT security pitfalls.",
    )

    text = (tmp_path / "wiki-map.md").read_text(encoding="utf-8")
    assert text.startswith("# Wiki Map")
    assert RECENT_SECTION_HEADING in text
    assert "obsidian-organize:wiki-map:auto-start" in text
    assert "obsidian-organize:wiki-map:auto-end" in text
    assert "[[wiki/ai-agent-wiki/jwt-pitfalls.md|JWT Pitfalls]]" in text
    assert "Common JWT security pitfalls." in text


def test_append_inserts_between_existing_markers(tmp_path):
    (tmp_path / "wiki-map.md").write_text(
        "# Wiki Map\n\n"
        "## Existing Section\n\n"
        "- [[wiki/old|stuff]]\n\n"
        "<!-- obsidian-organize:wiki-map:auto-start -->\n\n"
        f"## {RECENT_SECTION_HEADING.removeprefix('## ')}\n\n"
        "<!-- obsidian-organize:wiki-map:auto-end -->\n",
        encoding="utf-8",
    )

    append_wiki_map_row(
        tmp_path,
        domain="ai-agent-wiki",
        note_rel_path="wiki/ai-agent-wiki/new-note.md",
        title="New Note",
        summary="Newly added.",
    )

    text = (tmp_path / "wiki-map.md").read_text(encoding="utf-8")
    assert "[[wiki/ai-agent-wiki/new-note.md|New Note]]" in text
    # The existing section is preserved.
    assert "[[wiki/old|stuff]]" in text
    # The new row sits between the markers, not appended at the very end.
    end_idx = text.index("obsidian-organize:wiki-map:auto-end")
    new_idx = text.index("[[wiki/ai-agent-wiki/new-note.md")
    assert new_idx < end_idx


def test_append_appends_section_when_no_markers(tmp_path):
    """A user-managed wiki-map with themed sections but no markers must
    keep its content and gain the auto-section at the bottom."""
    (tmp_path / "wiki-map.md").write_text(
        "# Wiki Map\n\n"
        "## 🤖 AI Dev Tools\n\n"
        "- [[wiki/ai-agent-wiki/18-strix|Strix]] — pentest agent.\n",
        encoding="utf-8",
    )

    append_wiki_map_row(
        tmp_path,
        domain="ai-agent-wiki",
        note_rel_path="wiki/ai-agent-wiki/19-context-aware.md",
        title="Context-Aware Pentesting",
        summary="Strix's persistent threat-model layer.",
    )

    text = (tmp_path / "wiki-map.md").read_text(encoding="utf-8")
    # Prior themed section is untouched.
    assert "## 🤖 AI Dev Tools" in text
    assert "[[wiki/ai-agent-wiki/18-strix|Strix]]" in text
    # The auto-section was appended at the bottom with markers.
    assert text.rstrip().endswith("<!-- obsidian-organize:wiki-map:auto-end -->")
    assert "[[wiki/ai-agent-wiki/19-context-aware.md|Context-Aware Pentesting]]" in text


def test_append_is_idempotent(tmp_path):
    append_wiki_map_row(
        tmp_path,
        domain="ai-agent-wiki",
        note_rel_path="wiki/ai-agent-wiki/jwt-pitfalls.md",
        title="JWT Pitfalls",
        summary="Common JWT security pitfalls.",
    )
    first = (tmp_path / "wiki-map.md").read_text(encoding="utf-8")

    append_wiki_map_row(
        tmp_path,
        domain="ai-agent-wiki",
        note_rel_path="wiki/ai-agent-wiki/jwt-pitfalls.md",
        title="JWT Pitfalls",
        summary="Common JWT security pitfalls.",
    )
    second = (tmp_path / "wiki-map.md").read_text(encoding="utf-8")

    assert first == second


def test_append_uses_domain_to_pick_recent_section_label(tmp_path):
    """The auto-section records the domain in the summary so the user
    can see at a glance which wiki-domain each new note belongs to."""
    append_wiki_map_row(
        tmp_path,
        domain="system-design-wiki",
        note_rel_path="wiki/system-design-wiki/rate-limiter.md",
        title="Rate Limiter",
        summary="Counter-based limiter pattern.",
    )

    text = (tmp_path / "wiki-map.md").read_text(encoding="utf-8")
    assert "(system-design-wiki)" in text


# ---------------------------------------------------------------------------
# remove_wiki_map_row
# ---------------------------------------------------------------------------


def test_remove_drops_only_target_row(tmp_path):
    append_wiki_map_row(
        tmp_path,
        domain="ai-agent-wiki",
        note_rel_path="wiki/ai-agent-wiki/jwt-pitfalls.md",
        title="JWT Pitfalls",
        summary="Common JWT security pitfalls.",
    )
    append_wiki_map_row(
        tmp_path,
        domain="ai-agent-wiki",
        note_rel_path="wiki/ai-agent-wiki/session-tokens.md",
        title="Session Tokens",
        summary="Cookie-based sessions.",
    )

    remove_wiki_map_row(
        tmp_path,
        note_rel_path="wiki/ai-agent-wiki/jwt-pitfalls.md",
    )

    text = (tmp_path / "wiki-map.md").read_text(encoding="utf-8")
    assert "[[wiki/ai-agent-wiki/jwt-pitfalls.md" not in text
    assert "[[wiki/ai-agent-wiki/session-tokens.md|Session Tokens]]" in text


def test_remove_is_safe_when_row_absent(tmp_path):
    (tmp_path / "wiki-map.md").write_text(
        "# Wiki Map\n\n<!-- obsidian-organize:wiki-map:auto-start -->\n\n"
        "<!-- obsidian-organize:wiki-map:auto-end -->\n",
        encoding="utf-8",
    )
    # Should not raise.
    remove_wiki_map_row(
        tmp_path, note_rel_path="wiki/ai-agent-wiki/nonexistent.md"
    )
    text = (tmp_path / "wiki-map.md").read_text(encoding="utf-8")
    assert "obsidian-organize:wiki-map:auto-end" in text


def test_remove_on_missing_file_is_noop(tmp_path):
    # Should not raise.
    remove_wiki_map_row(
        tmp_path, note_rel_path="wiki/ai-agent-wiki/nonexistent.md"
    )
    assert not (tmp_path / "wiki-map.md").exists()
