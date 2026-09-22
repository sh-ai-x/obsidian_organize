"""Tests for `obsidian-organize:add_wiki` updating wiki-map.md + domain log.md.

The contract pinned here:

- Flat mode writes the leaf to ``wiki/<domain>/<slug>.md`` (not
  ``topics/<slug>.md``) and updates the root ``wiki-map.md`` plus the
  domain ``log.md``.
- Hierarchical mode writes the per-section leaves + sub-hub, and updates
  ``wiki-map.md`` + ``log.md`` with the sub-hub path (not individual
  leaves).
- Re-running for the same topic is idempotent on ``wiki-map.md`` and
  ``log.md``.
"""

from __future__ import annotations

from _lib import (
    parse_frontmatter,
    promote,
    resolve_hierarchical_paths,
    resolve_leaf_path,
    resolve_log_path,
    write_staged_file,
    write_hierarchical_staged_file,
    ResearchInput,
)
from _lib.wiki_map import RECENT_SECTION_HEADING


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_wiki_map(vault_root, body: str = "# Wiki Map\n"):
    (vault_root / "wiki-map.md").write_text(body, encoding="utf-8")


def _seed_wiki_domain(vault_root, domain: str = "ai-agent-wiki") -> None:
    (vault_root / "wiki" / domain).mkdir(parents=True, exist_ok=True)


def _make_flat_staged(vault_root, topic, *, fixed_now):
    write_staged_file(
        vault_root,
        ResearchInput(
            topic=topic,
            sources=["sources/source-a.md"],
            notes=["Insightful note about the topic."],
        ),
        now=fixed_now,
    )


def _make_hierarchical_staged(vault_root, topic, titles, *, fixed_now):
    body_parts = []
    for i, t in enumerate(titles, start=1):
        body_parts.append(f"## §{i} {t}\n")
        body_parts.append(f"Body for {t}.\n\n")
    body_parts.append("## Sources\n\n- (none)\n\n")
    body_parts.append("## Notes\n\n- (none)\n")
    write_hierarchical_staged_file(
        vault_root,
        topic,
        sections=[(i + 1, t) for i, t in enumerate(titles)],
        sources=["sources/source-a.md"],
        body="\n".join(body_parts),
        now=fixed_now,
    )


# ---------------------------------------------------------------------------
# Flat mode: destination path + side effects
# ---------------------------------------------------------------------------


def test_flat_mode_writes_to_wiki_domain_dir(vault_root, fixed_now):
    _seed_wiki_map(vault_root)
    _seed_wiki_domain(vault_root, "ai-agent-wiki")
    _make_flat_staged(vault_root, "jwt-pitfalls", fixed_now=fixed_now)

    result = promote(vault_root, "jwt-pitfalls", now=fixed_now)

    expected = resolve_leaf_path(vault_root, "ai-agent-wiki", "jwt-pitfalls")
    assert result.topic_path == expected
    assert result.topic_path.exists()
    # The flat mode must NOT use the legacy topics/ path.
    assert not (vault_root / "topics" / "jwt-pitfalls.md").exists()


def test_flat_mode_updates_wiki_map(vault_root, fixed_now):
    _seed_wiki_map(vault_root)
    _seed_wiki_domain(vault_root, "ai-agent-wiki")
    _make_flat_staged(vault_root, "jwt-pitfalls", fixed_now=fixed_now)

    promote(vault_root, "jwt-pitfalls", now=fixed_now)

    text = (vault_root / "wiki-map.md").read_text(encoding="utf-8")
    assert "[[wiki/ai-agent-wiki/jwt-pitfalls.md|Jwt Pitfalls]]" in text
    assert RECENT_SECTION_HEADING in text
    assert "(ai-agent-wiki)" in text


def test_flat_mode_appends_to_domain_log(vault_root, fixed_now):
    _seed_wiki_map(vault_root)
    _seed_wiki_domain(vault_root, "ai-agent-wiki")
    _make_flat_staged(vault_root, "jwt-pitfalls", fixed_now=fixed_now)

    promote(vault_root, "jwt-pitfalls", now=fixed_now)

    log = resolve_log_path(vault_root, "ai-agent-wiki")
    assert log.exists()
    log_text = log.read_text(encoding="utf-8")
    assert "# Ai Agent Wiki" in log_text or "# AI Agent Wiki" in log_text
    assert "jwt-pitfalls" in log_text
    assert "2026-09-05" in log_text


def test_flat_mode_wiki_map_is_idempotent(vault_root, fixed_now):
    _seed_wiki_map(vault_root)
    _seed_wiki_domain(vault_root, "ai-agent-wiki")
    _make_flat_staged(vault_root, "jwt-pitfalls", fixed_now=fixed_now)

    promote(vault_root, "jwt-pitfalls", now=fixed_now)
    first = (vault_root / "wiki-map.md").read_text(encoding="utf-8")

    # Force-overwrite and re-promote; wiki-map must not double-write.
    promote(vault_root, "jwt-pitfalls", force=True, now=fixed_now)
    second = (vault_root / "wiki-map.md").read_text(encoding="utf-8")
    assert first == second


# ---------------------------------------------------------------------------
# Domain detection for flat mode
# ---------------------------------------------------------------------------


def test_flat_mode_uses_explicit_domain_when_given(vault_root, fixed_now):
    _seed_wiki_map(vault_root)
    _seed_wiki_domain(vault_root, "ai-agent-wiki")
    _seed_wiki_domain(vault_root, "system-design-wiki")
    _make_flat_staged(vault_root, "rate-limiter", fixed_now=fixed_now)

    result = promote(
        vault_root, "rate-limiter", domain="system-design-wiki", now=fixed_now
    )

    expected = resolve_leaf_path(vault_root, "system-design-wiki", "rate-limiter")
    assert result.topic_path == expected


def test_flat_mode_autodetects_only_wiki_domain(vault_root, fixed_now):
    """When exactly one wiki/<domain>/ exists, the leaf lands there."""
    _seed_wiki_map(vault_root)
    _seed_wiki_domain(vault_root, "system-design-wiki")
    _make_flat_staged(vault_root, "rate-limiter", fixed_now=fixed_now)

    result = promote(vault_root, "rate-limiter", now=fixed_now)

    expected = resolve_leaf_path(vault_root, "system-design-wiki", "rate-limiter")
    assert result.topic_path == expected


# ---------------------------------------------------------------------------
# Hierarchical mode: side effects
# ---------------------------------------------------------------------------


def test_hierarchical_mode_updates_wiki_map_with_sub_hub(vault_root, fixed_now):
    _seed_wiki_map(vault_root)
    _seed_wiki_domain(vault_root, "ai-agent-wiki")
    titles = ["Section A", "Section B", "Section C", "Section D", "Section E"]
    _make_hierarchical_staged(
        vault_root, "core-ai-security-threats", titles, fixed_now=fixed_now
    )

    result = promote(
        vault_root, "core-ai-security-threats",
        hierarchical=True, domain="ai-agent-wiki",
        now=fixed_now,
    )

    text = (vault_root / "wiki-map.md").read_text(encoding="utf-8")
    # The sub-hub is the durable entry point, so the wiki-map links to it,
    # not to each per-section leaf.
    sub_hub_rel = str(result.sub_hub_path.relative_to(vault_root))
    assert f"[[{sub_hub_rel}" in text
    # Individual leaves must NOT have separate wiki-map rows.
    for leaf in result.leaf_paths:
        leaf_rel = str(leaf.relative_to(vault_root))
        assert f"[[{leaf_rel}" not in text


def test_hierarchical_mode_appends_to_domain_log(vault_root, fixed_now):
    _seed_wiki_map(vault_root)
    _seed_wiki_domain(vault_root, "ai-agent-wiki")
    titles = ["Section A", "Section B", "Section C", "Section D", "Section E"]
    _make_hierarchical_staged(
        vault_root, "core-ai-security-threats", titles, fixed_now=fixed_now
    )

    promote(
        vault_root, "core-ai-security-threats",
        hierarchical=True, domain="ai-agent-wiki",
        now=fixed_now,
    )

    log = resolve_log_path(vault_root, "ai-agent-wiki")
    log_text = log.read_text(encoding="utf-8")
    assert "core-ai-security-threats" in log_text
    # The log entry records the leaf count so users can see at a glance
    # how big the sub-tree is.
    assert "5" in log_text
