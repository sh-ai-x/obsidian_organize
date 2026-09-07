"""Tests for the hierarchical promotion mode of `add_wiki`.

When a staged research file has many numbered sections, the user can
opt in to a per-section leaf-note tree instead of a single flat topic
note. These tests pin the contract documented in
``add_wiki/SKILL.md`` § Hierarchical mode:

- A new ``wiki/<domain>/<slug>/<section>.md`` is written per section.
- A ``<slug>/_index.md`` sub-hub is auto-generated.
- With ``--major <name>``, a ``<major>/_index.md`` major hub is also
  written.
- The staged file's ``promoted_to`` points at the sub-hub, not any leaf.
"""

from __future__ import annotations

import pytest

from _lib import (
    parse_frontmatter,
    promote,
    resolve_staged_path,
    section_title_to_slug,
    write_hierarchical_staged_file,
)


# ---------------------------------------------------------------------------
# Section slug helper
# ---------------------------------------------------------------------------


def test_section_title_to_slug_basic():
    assert section_title_to_slug("OWASP LLM Top 10 — 2025 Edition") == "owasp-llm-top-10-2025-edition"


def test_section_title_to_slug_strips_trailing_punctuation():
    assert section_title_to_slug("Detection & Monitoring:") == "detection-monitoring"
    assert section_title_to_slug("Sandboxing.") == "sandboxing"


def test_section_title_to_slug_handles_pure_punctuation():
    assert section_title_to_slug("---") == "section"
    assert section_title_to_slug("") == "section"


def test_section_title_to_slug_respects_60_char_limit():
    long = "a" * 100
    out = section_title_to_slug(long)
    assert len(out) <= 60
    assert not out.endswith("-")


def test_section_title_to_slug_fallback_disambiguates_with_sec_num():
    """Two non-ASCII or pure-punctuation headings would otherwise both
    fall back to `section` and collide on the same leaf filename. When
    `sec_num` is provided the fallback is suffixed with the section
    number so each leaf lands at a unique path."""
    assert section_title_to_slug("---", sec_num=1) == "section-1"
    assert section_title_to_slug("---", sec_num=7) == "section-7"
    assert section_title_to_slug("", sec_num=2) == "section-2"
    # Without sec_num the legacy fallback still applies (back-compat).
    assert section_title_to_slug("---") == "section"
    assert section_title_to_slug("") == "section"


# ---------------------------------------------------------------------------
# Test helper
# ---------------------------------------------------------------------------


def _write_sectioned_staged_file(vault_root, topic, section_titles, *, fixed_now):
    """Stage a research file whose body has H2 ``## §N Title`` sections.

    Each section gets a body line so the leaf writer has something to
    wrap. Returns the staged file's resolved path.
    """
    body_parts = []
    for i, title in enumerate(section_titles, start=1):
        body_parts.append(f"## §{i} {title}\n")
        body_parts.append(f"Body for {title}.\n\n")
    body_parts.append("## Sources\n\n- (none)\n\n")
    body_parts.append("## Notes\n\n- (none)\n")
    return write_hierarchical_staged_file(
        vault_root,
        topic,
        sections=[(i + 1, t) for i, t in enumerate(section_titles)],
        sources=["sources/source-a.md"],
        body="\n".join(body_parts),
        now=fixed_now,
    )


# ---------------------------------------------------------------------------
# Hierarchical promotion: no --major (2-level: domain/slug)
# ---------------------------------------------------------------------------


def test_hierarchical_promotion_creates_per_section_leaves(vault_root, fixed_now):
    titles = [
        "Executive Summary",
        "OWASP LLM Top 10",
        "Prompt Injection",
        "Jailbreaks",
        "Detection Monitoring",
    ]
    _write_sectioned_staged_file(vault_root, "core-ai-security-threats", titles, fixed_now=fixed_now)

    result = promote(
        vault_root, "core-ai-security-threats",
        hierarchical=True, domain="ai-agent-wiki",
        now=fixed_now,
    )

    # 5 leaves + 1 sub-hub
    assert len(result.leaf_paths) == 5, f"expected 5 leaves, got {len(result.leaf_paths)}: {result.leaf_paths}"
    assert all(p.exists() for p in result.leaf_paths)
    assert result.sub_hub_path is not None and result.sub_hub_path.exists()
    assert result.major_hub_path is None

    for leaf, title in zip(result.leaf_paths, titles):
        fm, body = parse_frontmatter(leaf.read_text(encoding="utf-8"))
        assert fm["topic"] == "core-ai-security-threats"
        assert fm["status"] == "active"
        assert "tags" in fm
        assert body.lstrip().startswith(f"# {title}")


def test_hierarchical_promotion_sub_hub_lists_all_leaves(vault_root, fixed_now):
    titles = ["Section A", "Section B", "Section C", "Section D", "Section E"]
    _write_sectioned_staged_file(vault_root, "test-topic", titles, fixed_now=fixed_now)

    result = promote(
        vault_root, "test-topic",
        hierarchical=True, domain="ai-agent-wiki",
        now=fixed_now,
    )

    assert result.sub_hub_path is not None
    sub_text = result.sub_hub_path.read_text(encoding="utf-8")
    for leaf in result.leaf_paths:
        slug = leaf.stem
        assert f"[[{slug}" in sub_text, f"sub-hub missing link to {slug}"


def test_hierarchical_promotion_marks_staged_to_sub_hub(vault_root, fixed_now):
    titles = ["One", "Two", "Three", "Four", "Five"]
    _write_sectioned_staged_file(vault_root, "test-topic", titles, fixed_now=fixed_now)

    result = promote(
        vault_root, "test-topic",
        hierarchical=True, domain="ai-agent-wiki",
        now=fixed_now,
    )

    staged_fm, _ = parse_frontmatter(
        resolve_staged_path(vault_root, "test-topic").read_text(encoding="utf-8")
    )
    assert staged_fm["status"] == "promoted"
    assert staged_fm["promoted_to"] == str(
        result.sub_hub_path.relative_to(vault_root)
    )


# ---------------------------------------------------------------------------
# Hierarchical promotion: with --major (3-level: domain/major/slug)
# ---------------------------------------------------------------------------


def test_hierarchical_promotion_with_major_writes_major_hub(vault_root, fixed_now):
    titles = ["S1", "S2", "S3", "S4", "S5"]
    _write_sectioned_staged_file(vault_root, "threats", titles, fixed_now=fixed_now)

    result = promote(
        vault_root, "threats",
        hierarchical=True, major="core-ai-security", domain="ai-agent-wiki",
        now=fixed_now,
    )

    assert result.major_hub_path is not None
    assert result.major_hub_path.exists()
    major_text = result.major_hub_path.read_text(encoding="utf-8")
    assert "## Sub-Domains" in major_text
    assert "[[threats/_index" in major_text or "[[threats" in major_text
    expected_dir = vault_root / "wiki" / "ai-agent-wiki" / "core-ai-security" / "threats"
    assert result.sub_hub_path.parent == expected_dir
    for leaf in result.leaf_paths:
        assert leaf.parent == expected_dir


# ---------------------------------------------------------------------------
# Auto-enable threshold
# ---------------------------------------------------------------------------


def test_hierarchical_auto_enables_at_5_sections(vault_root, fixed_now):
    titles = ["A", "B", "C", "D", "E"]
    _write_sectioned_staged_file(vault_root, "auto-topic", titles, fixed_now=fixed_now)

    # No explicit hierarchical flag; >= 5 sections should auto-enable.
    result = promote(vault_root, "auto-topic", domain="ai-agent-wiki", now=fixed_now)
    assert len(result.leaf_paths) == 5, "expected auto-enable at 5 sections"


def test_hierarchical_stays_flat_below_5_sections(vault_root, fixed_now):
    titles = ["Only", "Two", "Sections"]
    _write_sectioned_staged_file(vault_root, "small-topic", titles, fixed_now=fixed_now)

    result = promote(vault_root, "small-topic", domain="ai-agent-wiki", now=fixed_now)
    assert result.leaf_paths == []
    assert result.sub_hub_path is None


def test_hierarchical_force_off_below_threshold(vault_root, fixed_now):
    titles = ["A", "B", "C", "D", "E", "F"]  # would auto-enable
    _write_sectioned_staged_file(vault_root, "explicit-topic", titles, fixed_now=fixed_now)

    result = promote(
        vault_root, "explicit-topic", domain="ai-agent-wiki",
        no_hierarchical=True, now=fixed_now,
    )
    assert result.leaf_paths == []
    assert result.sub_hub_path is None


# ---------------------------------------------------------------------------
# Section parser edge cases
# ---------------------------------------------------------------------------


def test_hierarchical_supports_h3_numbered_sections(vault_root, fixed_now):
    """A research file with ``### 1. Title`` H3 sections (no H2 numbering)
    should also be parsed and split into leaves."""
    body = (
        "### 1. First\nBody of first.\n\n"
        "### 2. Second\nBody of second.\n\n"
        "### 3. Third\nBody of third.\n\n"
        "### 4. Fourth\nBody of fourth.\n\n"
        "### 5. Fifth\nBody of fifth.\n\n"
        "## Sources\n\n- (none)\n\n"
        "## Notes\n\n- (none)\n"
    )
    write_hierarchical_staged_file(
        vault_root, "h3-topic",
        sections=[(i, f"Section{i}") for i in range(1, 6)],
        sources=[],
        body=body,
        now=fixed_now,
    )
    result = promote(
        vault_root, "h3-topic",
        hierarchical=True, domain="ai-agent-wiki",
        now=fixed_now,
    )
    assert len(result.leaf_paths) == 5
    for leaf in result.leaf_paths:
        assert leaf.exists()


def test_hierarchical_refuses_zero_sections(vault_root, fixed_now):
    """An unparseable research file (no numbered H2/H3 sections) should
    raise a clear error rather than silently falling back to flat."""
    body = "Just some prose, no numbered headings.\n\nMore prose.\n"
    write_hierarchical_staged_file(
        vault_root, "nosections",
        sections=[],
        sources=[],
        body=body,
        now=fixed_now,
    )
    with pytest.raises(ValueError, match="no parseable sections"):
        promote(
            vault_root, "nosections",
            hierarchical=True, domain="ai-agent-wiki",
            now=fixed_now,
        )


# ---------------------------------------------------------------------------
# Backwards compatibility
# ---------------------------------------------------------------------------


def test_flat_mode_still_writes_to_topics_dir(vault_root, fixed_now):
    """Existing flat-mode behavior must be preserved: 1-3 sections stay flat
    and write to ``topics/<slug>.md``, not ``wiki/<domain>/...``."""
    titles = ["Only", "Two", "Sections"]
    _write_sectioned_staged_file(vault_root, "flat-topic", titles, fixed_now=fixed_now)

    result = promote(vault_root, "flat-topic", domain="ai-agent-wiki", now=fixed_now)
    assert result.leaf_paths == []
    assert result.sub_hub_path is None
    assert result.topic_path == vault_root / "topics" / "flat-topic.md"
    assert result.topic_path.exists()
