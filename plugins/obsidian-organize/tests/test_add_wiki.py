"""Tests for `obsidian-organize:add_wiki` flat-mode path + side effects.

Flat mode (the default) writes a leaf to ``wiki/<domain>/<slug>.md``,
adds a back-link marker to each cited source, and marks the staged
file as promoted. These tests pin the flat-mode contract — the wiki-map
+ log.md auto-update is covered separately in
``test_add_wiki_wiki_map.py``.
"""

from __future__ import annotations

from _lib import (
    BACKLINK_MARKER_TEMPLATE,
    detect_wiki_domain,
    parse_frontmatter,
    promote,
    resolve_leaf_path,
    resolve_staged_path,
    write_staged_file,
    ResearchInput,
)


def _seed_domain(vault_root, domain: str) -> None:
    (vault_root / "wiki" / domain).mkdir(parents=True, exist_ok=True)


def test_add_wiki_promotes_staged_to_leaf_note(vault_root, fixed_now):
    domain = detect_wiki_domain(vault_root)
    _seed_domain(vault_root, domain)
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

    expected = resolve_leaf_path(vault_root, domain, "hermes-protocol")
    assert result.topic == "hermes-protocol"
    assert result.topic_path == expected
    assert result.topic_path.exists()

    fm, body = parse_frontmatter(result.topic_path.read_text(encoding="utf-8"))
    assert fm["topic"] == "hermes-protocol"
    assert fm["domain"] == domain
    assert fm["status"] == "active"
    assert fm["tags"] == ["hermes-protocol"]
    assert fm["sources"] == ["sources/source-a.md", "sources/source-b.md"]
    assert "## Summary" in body
    assert "## Sources" in body

    staged_fm, _ = parse_frontmatter(
        resolve_staged_path(vault_root, "hermes-protocol").read_text(encoding="utf-8")
    )
    assert staged_fm["status"] == "promoted"
    assert staged_fm["promoted_to"] == f"wiki/{domain}/hermes-protocol.md"


def test_add_wiki_adds_backlinks_to_source_files(vault_root, fixed_now):
    domain = detect_wiki_domain(vault_root)
    _seed_domain(vault_root, domain)
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
        domain=domain,
        topic="hermes-protocol",
        timestamp=fixed_now.isoformat(timespec="seconds"),
    )
    for src in ("sources/source-a.md", "sources/source-b.md"):
        text = (vault_root / src).read_text(encoding="utf-8")
        assert expected_marker in text, f"missing back-link in {src}"


def test_add_wiki_refuses_existing_topic_without_force(vault_root, fixed_now):
    domain = detect_wiki_domain(vault_root)
    _seed_domain(vault_root, domain)
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
    raise AssertionError("expected FileExistsError on duplicate leaf note")


def test_add_wiki_force_overwrites_existing_leaf(vault_root, fixed_now):
    domain = detect_wiki_domain(vault_root)
    _seed_domain(vault_root, domain)
    write_staged_file(
        vault_root,
        ResearchInput(topic="hermes-protocol", sources=["sources/source-a.md"]),
        now=fixed_now,
    )
    promote(vault_root, "hermes-protocol", now=fixed_now)
    # Promote again with --force; should not raise.
    promote(vault_root, "hermes-protocol", force=True, now=fixed_now)
    assert resolve_leaf_path(vault_root, domain, "hermes-protocol").exists()


def test_add_wiki_fails_without_staged_research(vault_root, fixed_now):
    try:
        promote(vault_root, "ghost-topic", now=fixed_now)
    except FileNotFoundError:
        return
    raise AssertionError("expected FileNotFoundError on missing staged file")
