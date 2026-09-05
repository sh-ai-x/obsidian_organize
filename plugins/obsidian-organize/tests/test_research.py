"""Tests for the `obsidian-organize:research` skill's deterministic helper."""

from __future__ import annotations

from _lib import (
    parse_frontmatter,
    resolve_staged_path,
    validate_topic_slug,
    write_staged_file,
    ResearchInput,
)


def test_research_creates_staged_file_with_frontmatter(vault_root, fixed_now):
    result = write_staged_file(
        vault_root,
        ResearchInput(
            topic="Hermes Protocol",
            sources=[
                "https://example.com/hermes-spec",
                "sources/source-a.md",
            ],
            notes=["Length-prefixed frames with 4-byte header."],
        ),
        now=fixed_now,
    )

    assert result.topic == "hermes-protocol"
    assert result.staged_path == resolve_staged_path(vault_root, "hermes-protocol")
    assert result.staged_path.exists()

    text = result.staged_path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    assert fm["topic"] == "hermes-protocol"
    assert fm["created"] == "2026-09-05T12:00:00+00:00"
    assert fm["status"] == "staged"
    assert fm["sources"] == [
        "https://example.com/hermes-spec",
        "sources/source-a.md",
    ]
    assert "## Sources" in body
    assert "## Notes" in body
    assert "Length-prefixed frames" in body


def test_research_refuses_overwrite_without_append(vault_root, fixed_now):
    write_staged_file(
        vault_root,
        ResearchInput(topic="hermes-protocol", sources=["a"]),
        now=fixed_now,
    )
    try:
        write_staged_file(
            vault_root,
            ResearchInput(topic="hermes-protocol", sources=["b"]),
            now=fixed_now,
        )
    except FileExistsError:
        return
    raise AssertionError("expected FileExistsError on overwrite without append")


def test_research_append_extends_sources(vault_root, fixed_now):
    from datetime import datetime, timedelta, timezone

    write_staged_file(
        vault_root,
        ResearchInput(topic="hermes-protocol", sources=["a"]),
        now=fixed_now,
    )
    later = fixed_now + timedelta(seconds=30)
    write_staged_file(
        vault_root,
        ResearchInput(topic="hermes-protocol", sources=["b"], notes=["extra"]),
        now=later,
        append=True,
    )
    text = resolve_staged_path(vault_root, "hermes-protocol").read_text(encoding="utf-8")
    fm, _ = parse_frontmatter(text)
    assert fm["sources"] == ["a", "b"]
    assert fm["updated"] == later.isoformat(timespec="seconds")


def test_research_rejects_invalid_slug(vault_root):
    try:
        validate_topic_slug("Invalid Slug With Spaces")
    except ValueError:
        return
    raise AssertionError("expected ValueError for invalid slug")
