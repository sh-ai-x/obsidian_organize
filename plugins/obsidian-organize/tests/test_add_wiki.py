"""Tests for `obsidian-organize:add_wiki`."""

from __future__ import annotations

from _lib import (
    BACKLINK_MARKER_TEMPLATE,
    parse_frontmatter,
    promote,
    resolve_staged_path,
    resolve_topic_path,
    write_staged_file,
    ResearchInput,
)


def test_add_wiki_promotes_staged_to_topic_note(vault_root, fixed_now):
    write_staged_file(
        vault_root,
        ResearchInput(
            topic="hermes-protocol",
            sources=["sources/source-a.md", "sources/source-b.md"],
            notes=["Framing layer summary."],
        ),
        now=fixed_now,
    )

    result = promote(vault_root, "hermes-protocol", now=fixed_now)

    assert result.topic == "hermes-protocol"
    assert result.topic_path == resolve_topic_path(vault_root, "hermes-protocol")
    assert result.topic_path.exists()

    fm, body = parse_frontmatter(result.topic_path.read_text(encoding="utf-8"))
    assert fm["topic"] == "hermes-protocol"
    assert fm["status"] == "active"
    assert fm["tags"] == ["topic/hermes-protocol"]
    assert fm["sources"] == ["sources/source-a.md", "sources/source-b.md"]
    assert "## Summary" in body
    assert "## Sources" in body

    staged_fm, _ = parse_frontmatter(
        resolve_staged_path(vault_root, "hermes-protocol").read_text(encoding="utf-8")
    )
    assert staged_fm["status"] == "promoted"
    assert staged_fm["promoted_to"] == "topics/hermes-protocol.md"


def test_add_wiki_adds_backlinks_to_source_files(vault_root, fixed_now):
    write_staged_file(
        vault_root,
        ResearchInput(
            topic="hermes-protocol",
            sources=["sources/source-a.md", "sources/source-b.md"],
        ),
        now=fixed_now,
    )
    promote(vault_root, "hermes-protocol", now=fixed_now)

    expected_marker = BACKLINK_MARKER_TEMPLATE.format(
        topic="hermes-protocol",
        timestamp=fixed_now.isoformat(timespec="seconds"),
    )
    for src in ("sources/source-a.md", "sources/source-b.md"):
        text = (vault_root / src).read_text(encoding="utf-8")
        assert expected_marker in text, f"missing back-link in {src}"


def test_add_wiki_refuses_existing_topic_without_force(vault_root, fixed_now):
    write_staged_file(
        vault_root,
        ResearchInput(topic="hermes-protocol", sources=[]),
        now=fixed_now,
    )
    promote(vault_root, "hermes-protocol", now=fixed_now)
    try:
        promote(vault_root, "hermes-protocol", now=fixed_now)
    except FileExistsError:
        return
    raise AssertionError("expected FileExistsError on duplicate topic note")


def test_add_wiki_force_overwrites_existing_topic(vault_root, fixed_now):
    write_staged_file(
        vault_root,
        ResearchInput(topic="hermes-protocol", sources=["sources/source-a.md"]),
        now=fixed_now,
    )
    promote(vault_root, "hermes-protocol", now=fixed_now)
    # Promote again with --force; should not raise.
    promote(vault_root, "hermes-protocol", force=True, now=fixed_now)
    assert resolve_topic_path(vault_root, "hermes-protocol").exists()


def test_add_wiki_fails_without_staged_research(vault_root, fixed_now):
    try:
        promote(vault_root, "ghost-topic", now=fixed_now)
    except FileNotFoundError:
        return
    raise AssertionError("expected FileNotFoundError on missing staged file")
