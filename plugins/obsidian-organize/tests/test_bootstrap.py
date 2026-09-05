"""Tests for `obsidian-organize:bootstrap`."""

from __future__ import annotations

from _lib.bootstrap import bootstrap


def test_bootstrap_creates_canonical_layout(vault_root, fixed_now):
    result = bootstrap(vault_root, now=fixed_now)

    assert (vault_root / "Clippings").is_dir()
    assert (vault_root / "Clippings" / "processed").is_dir()
    assert (vault_root / "Clippings" / ".keep").exists()
    assert (vault_root / "Clippings" / "processed" / ".keep").exists()
    assert (vault_root / "wiki").is_dir()
    assert (vault_root / "wiki" / ".keep").exists()
    assert (vault_root / "_research").is_dir()
    assert (vault_root / "_research" / ".keep").exists()
    assert (vault_root / "_archive" / "research").is_dir()
    assert (vault_root / "_archive" / "research" / ".keep").exists()
    assert (vault_root / "topics").is_dir()
    assert result.wiki_map_written is True


def test_bootstrap_writes_wiki_map_template_with_markers(vault_root, fixed_now):
    bootstrap(vault_root, now=fixed_now)

    text = (vault_root / "wiki-map.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "type: wiki-map" in text
    assert "obsidian-organize:wiki-map:auto-start" in text
    assert "obsidian-organize:wiki-map:auto-end" in text
    assert "# Wiki Map" in text
    assert "## Topics" in text


def test_bootstrap_seeds_topic_subdirs_when_requested(vault_root, fixed_now):
    result = bootstrap(
        vault_root,
        topics=["Hermes Protocol", "wire-protocols"],
        now=fixed_now,
    )

    assert "hermes-protocol" in result.seeded_topics
    assert "wire-protocols" in result.seeded_topics
    for slug in ("hermes-protocol", "wire-protocols"):
        d = vault_root / "wiki" / slug
        assert d.is_dir()
        assert (d / ".keep").exists()
        readme = d / "README.md"
        assert readme.exists()
        body = readme.read_text(encoding="utf-8")
        assert f"topic: {slug}" in body
        assert "seeded-by: bootstrap" in body


def test_bootstrap_refuses_to_clobber_existing_layout(vault_root, fixed_now):
    bootstrap(vault_root, now=fixed_now)
    sentinel = vault_root / "wiki" / "user-note.md"
    sentinel.write_text("do not delete me", encoding="utf-8")

    bootstrap(vault_root, now=fixed_now)
    assert sentinel.exists()
    assert sentinel.read_text(encoding="utf-8") == "do not delete me"


def test_bootstrap_force_overwrites(vault_root, fixed_now):
    bootstrap(vault_root, now=fixed_now)
    (vault_root / "wiki-map.md").unlink()
    result = bootstrap(vault_root, force=True, now=fixed_now)
    assert result.wiki_map_written is True
    assert (vault_root / "wiki-map.md").exists()
