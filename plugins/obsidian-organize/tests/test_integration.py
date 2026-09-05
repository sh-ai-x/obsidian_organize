"""End-to-end integration test: research → add_wiki → remove_wiki on one topic."""

from __future__ import annotations

from _lib import (
    BACKLINK_MARKER_TEMPLATE,
    parse_frontmatter,
    promote,
    resolve_archive_path,
    resolve_staged_path,
    resolve_topic_path,
    retire,
    write_staged_file,
    ResearchInput,
)


def test_full_lifecycle_research_then_add_wiki_then_remove_wiki(vault_root, fixed_now):
    topic = "hermes-protocol"

    # 1. research
    write_staged_file(
        vault_root,
        ResearchInput(
            topic=topic,
            sources=["sources/source-a.md", "sources/source-b.md"],
            notes=["Length-prefixed frames.", "4-byte big-endian header."],
        ),
        now=fixed_now,
    )
    staged = resolve_staged_path(vault_root, topic)
    assert staged.exists()

    # 2. add_wiki
    promotion = promote(vault_root, topic, now=fixed_now)
    topic_path = promotion.topic_path
    assert topic_path.exists()

    # Topic note frontmatter is sane.
    fm, _ = parse_frontmatter(topic_path.read_text(encoding="utf-8"))
    assert fm["status"] == "active"
    assert fm["topic"] == topic
    assert fm["tags"] == [f"topic/{topic}"]

    # Back-links present.
    expected_marker = BACKLINK_MARKER_TEMPLATE.format(
        topic=topic, timestamp=fixed_now.isoformat(timespec="seconds")
    )
    for src in ("sources/source-a.md", "sources/source-b.md"):
        assert expected_marker in (vault_root / src).read_text(encoding="utf-8")

    # 3. remove_wiki
    result = retire(vault_root, topic, now=fixed_now)

    # Topic note gone, staged file archived, back-links stripped.
    assert not topic_path.exists()
    assert not staged.exists()
    assert result.archived_to is not None
    assert result.archived_to.exists()
    archived_fm, _ = parse_frontmatter(result.archived_to.read_text(encoding="utf-8"))
    assert archived_fm["status"] == "archived"
    for src in ("sources/source-a.md", "sources/source-b.md"):
        assert "[[topics/hermes-protocol]]" not in (
            vault_root / src
        ).read_text(encoding="utf-8")


def test_lifecycle_with_keep_staged(vault_root, fixed_now):
    topic = "wire-protocols"
    write_staged_file(
        vault_root,
        ResearchInput(
            topic=topic,
            sources=["sources/source-a.md"],
            notes=["Cross-cutting protocol notes."],
        ),
        now=fixed_now,
    )
    promote(vault_root, topic, now=fixed_now)
    result = retire(vault_root, topic, keep_staged=True, now=fixed_now)

    assert result.archived_to == resolve_staged_path(vault_root, topic)
    fm, _ = parse_frontmatter(
        resolve_staged_path(vault_root, topic).read_text(encoding="utf-8")
    )
    assert fm["status"] == "archived"
    assert not resolve_topic_path(vault_root, topic).exists()
