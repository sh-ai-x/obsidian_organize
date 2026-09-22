"""End-to-end integration test: research → add_wiki → remove_wiki on one topic."""

from __future__ import annotations

from _lib import (
    BACKLINK_MARKER_TEMPLATE,
    detect_wiki_domain,
    parse_frontmatter,
    promote,
    resolve_archive_path,
    resolve_leaf_path,
    resolve_staged_path,
    retire,
    write_staged_file,
    ResearchInput,
)


def _seed_domain(vault_root) -> str:
    domain = detect_wiki_domain(vault_root)
    (vault_root / "wiki" / domain).mkdir(parents=True, exist_ok=True)
    return domain


def test_full_lifecycle_research_then_add_wiki_then_remove_wiki(vault_root, fixed_now):
    topic = "hermes-protocol"
    domain = _seed_domain(vault_root)

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
    leaf_path = promotion.topic_path
    assert leaf_path == resolve_leaf_path(vault_root, domain, topic)
    assert leaf_path.exists()

    # Leaf frontmatter is sane.
    fm, _ = parse_frontmatter(leaf_path.read_text(encoding="utf-8"))
    assert fm["status"] == "active"
    assert fm["topic"] == topic
    assert fm["domain"] == domain

    # Back-links present (marker is keyed to the new wiki-domain path).
    expected_marker = BACKLINK_MARKER_TEMPLATE.format(
        domain=domain, topic=topic,
        timestamp=fixed_now.isoformat(timespec="seconds"),
    )
    for src in ("sources/source-a.md", "sources/source-b.md"):
        assert expected_marker in (vault_root / src).read_text(encoding="utf-8")

    # 3. remove_wiki
    result = retire(vault_root, topic, now=fixed_now)

    # Leaf gone, staged file archived, back-links stripped, wiki-map row gone.
    assert not leaf_path.exists()
    assert not staged.exists()
    assert result.archived_to is not None
    assert result.archived_to.exists()
    archived_fm, _ = parse_frontmatter(result.archived_to.read_text(encoding="utf-8"))
    assert archived_fm["status"] == "archived"
    for src in ("sources/source-a.md", "sources/source-b.md"):
        assert f"[[wiki/{domain}/{topic}]]" not in (
            vault_root / src
        ).read_text(encoding="utf-8")
    assert result.wiki_map_row_removed is True
    wiki_map = (vault_root / "wiki-map.md").read_text(encoding="utf-8")
    assert f"wiki/{domain}/{topic}.md" not in wiki_map


def test_lifecycle_with_keep_staged(vault_root, fixed_now):
    topic = "wire-protocols"
    _seed_domain(vault_root)
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
    domain = detect_wiki_domain(vault_root)
    assert not resolve_leaf_path(vault_root, domain, topic).exists()
