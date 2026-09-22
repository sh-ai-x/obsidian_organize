"""Tests for `obsidian-organize:remove_wiki`."""

from __future__ import annotations

from _lib import (
    detect_wiki_domain,
    parse_frontmatter,
    promote,
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


def _promote(vault_root, fixed_now, topic="hermes-protocol"):
    domain = _seed_domain(vault_root)
    write_staged_file(
        vault_root,
        ResearchInput(
            topic=topic,
            sources=["sources/source-a.md", "sources/source-b.md"],
        ),
        now=fixed_now,
    )
    return promote(vault_root, topic, now=fixed_now)


def test_remove_wiki_dry_run_does_not_mutate(vault_root, fixed_now):
    domain = _seed_domain(vault_root)
    _promote(vault_root, fixed_now)
    result = retire(vault_root, "hermes-protocol", dry_run=True, now=fixed_now)

    assert result.dry_run is True
    assert result.topic_note_deleted is True
    assert resolve_leaf_path(vault_root, domain, "hermes-protocol").exists()
    assert resolve_staged_path(vault_root, "hermes-protocol").exists()


def test_remove_wiki_archives_staged_and_deletes_leaf(vault_root, fixed_now):
    domain = _seed_domain(vault_root)
    _promote(vault_root, fixed_now)
    result = retire(vault_root, "hermes-protocol", now=fixed_now)

    assert result.dry_run is False
    assert result.topic_note_deleted is True
    assert not resolve_leaf_path(vault_root, domain, "hermes-protocol").exists()
    assert not resolve_staged_path(vault_root, "hermes-protocol").exists()
    assert result.archived_to is not None
    assert result.archived_to.exists()
    assert result.archived_to.read_text(encoding="utf-8").startswith("---\n")

    # Archived file's status must be 'archived'.
    fm, _ = parse_frontmatter(result.archived_to.read_text(encoding="utf-8"))
    assert fm["status"] == "archived"


def test_remove_wiki_strips_backlinks_from_source_files(vault_root, fixed_now):
    domain = _seed_domain(vault_root)
    _promote(vault_root, fixed_now)
    retire(vault_root, "hermes-protocol", now=fixed_now)

    for src in ("sources/source-a.md", "sources/source-b.md"):
        text = (vault_root / src).read_text(encoding="utf-8")
        assert f"[[wiki/{domain}/hermes-protocol]]" not in text, f"back-link leaked in {src}"


def test_remove_wiki_keep_staged_marks_archived_in_place(vault_root, fixed_now):
    _seed_domain(vault_root)
    _promote(vault_root, fixed_now)
    result = retire(
        vault_root, "hermes-protocol", keep_staged=True, now=fixed_now
    )

    assert result.archived_to == resolve_staged_path(vault_root, "hermes-protocol")
    assert result.archived_to.exists()
    fm, _ = parse_frontmatter(result.archived_to.read_text(encoding="utf-8"))
    assert fm["status"] == "archived"


def test_remove_wiki_fails_without_leaf_note(vault_root, fixed_now):
    try:
        retire(vault_root, "ghost-topic", now=fixed_now)
    except FileNotFoundError:
        return
    raise AssertionError("expected FileNotFoundError on missing leaf note")


def test_remove_wiki_drops_wiki_map_row(vault_root, fixed_now):
    """remove_wiki must drop the row added by add_wiki."""
    domain = _seed_domain(vault_root)
    _promote(vault_root, fixed_now)

    wiki_map = vault_root / "wiki-map.md"
    before = wiki_map.read_text(encoding="utf-8")
    assert f"wiki/{domain}/hermes-protocol.md" in before

    retire(vault_root, "hermes-protocol", now=fixed_now)

    after = wiki_map.read_text(encoding="utf-8")
    assert f"wiki/{domain}/hermes-protocol.md" not in after
