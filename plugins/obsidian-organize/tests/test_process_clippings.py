"""Tests for `obsidian-organize:process_clippings`.

process_clippings scans `<vault>/Clippings/` (excluding `processed/`) and
for every `.md` file:

  1. Derives a topic slug from the first H1 in the body (fallback: filename).
  2. Creates `wiki/<topic>/README.md` (LLM-Wiki style) if missing.
  3. Creates `wiki/<topic>/clippings/<safe-name>.md` with a frontmatter
     envelope + the original body verbatim.
  4. Moves the source file to `Clippings/processed/<safe-name>.md`.
  5. Appends a row to `wiki-map.md` (creates the file with the template
     if missing).

Run with: `pytest -q tests/test_process_clippings.py`
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _lib import (
    ClippingPage,
    ProcessClippingsResult,
    extract_topic_slug,
    process_clippings,
    render_clipping_page,
    render_topic_readme,
    resolve_clipping_page,
    resolve_processed_path,
    resolve_topic_dir,
    unique_processed_path,
)


# ---------- pure-function tests (no vault) ---------------------------------


def test_extract_topic_slug_from_h1() -> None:
    text = "# AI Security Career Roadmap\n\nBody…"
    assert extract_topic_slug(text, "2026년_09월_05일_AI_보안_취업_로드맵.md") == "ai-security-career-roadmap"


def test_extract_topic_slug_from_filename_when_no_h1() -> None:
    text = "no heading here, just prose"
    assert extract_topic_slug(text, "LangChain_Research_2026-09-05.md") == "langchain-research-2026-09-05"


def test_extract_topic_slug_handles_non_ascii() -> None:
    # Korean / mixed-script headings collapse to a slug-friendly form; if the
    # result is empty (no ASCII chars survived), fall back to the filename.
    text = "# 한경 보안 리서치\n\n"
    slug = extract_topic_slug(text, "한국_보안_리서치.md")
    assert slug == "한국-보안-리서치" or slug == "한국-보안-리서치"


def test_render_topic_readme_template() -> None:
    out = render_topic_readme(topic="ai-security", created_iso="2026-09-05T12:00:00Z")
    assert "# ai-security" in out
    assert "Karpathy-style LLM Wiki" in out
    assert "Created: 2026-09-05T12:00:00Z" in out
    # Auto-marker block for `add_wiki`-style appenders.
    assert "<!-- obsidian-organize:topic:auto-start -->" in out
    assert "<!-- obsidian-organize:topic:auto-end -->" in out


def test_render_clipping_page_envelope() -> None:
    page = render_clipping_page(
        source_filename="2026년_09월_05일_AI_보안_리서치.md",
        topic="ai-security",
        body="# AI 보안 리서치\n\n본문…",
        processed_iso="2026-09-05T12:00:00Z",
    )
    assert page.startswith("---\n")
    assert "type: clipping" in page
    assert "topic: ai-security" in page
    assert "source: 2026년_09월_05일_AI_보안_리서치.md" in page
    # `processed_iso` contains `:` so the serializer quotes it — that's valid YAML.
    assert "processed:" in page and "2026-09-05T12:00:00Z" in page
    assert "# AI 보안 리서치" in page


def test_resolve_topic_dir() -> None:
    assert resolve_topic_dir(Path("/vault"), "ai-security") == Path("/vault/wiki/ai-security")


def test_resolve_clipping_page() -> None:
    p = resolve_clipping_page(Path("/vault"), "ai-security", "My Clipping.md")
    assert p == Path("/vault/wiki/ai-security/clippings/My Clipping.md")


def test_unique_processed_path_no_collision(tmp_path: Path) -> None:
    # Nothing exists yet — desired target returned as-is.
    p = unique_processed_path(tmp_path, "a.md")
    assert p == tmp_path / "a.md"


def test_unique_processed_path_with_collision(tmp_path: Path) -> None:
    # The desired target already exists → must be disambiguated.
    (tmp_path / "a.md").touch()
    p = unique_processed_path(tmp_path, "a.md")
    assert p != tmp_path / "a.md"
    assert p.name.startswith("a-")
    assert p.suffix == ".md"


# ---------- end-to-end tests against a real vault ---------------------------


def _write_clipping(vault: Path, name: str, body: str) -> Path:
    d = vault / "Clippings"
    d.mkdir(exist_ok=True)
    p = d / name
    p.write_text(body, encoding="utf-8")
    return p


def test_process_clippings_empty_clippings_is_noop(vault_root: Path, fixed_now) -> None:
    (vault_root / "Clippings").mkdir(exist_ok=True)
    result = process_clippings(vault_root, now=fixed_now, dry_run=False)
    assert result.processed == []
    assert result.skipped == []
    assert not (vault_root / "wiki").exists()


def test_process_clippings_single_clipping_creates_wiki_entry(
    vault_root: Path, fixed_now
) -> None:
    src = _write_clipping(
        vault_root,
        "2026-09-05_AI_Security_Research.md",
        "# AI Security Research\n\nBody line 1.\nBody line 2.\n",
    )
    result = process_clippings(vault_root, now=fixed_now, dry_run=False)

    # Returns metadata
    assert len(result.processed) == 1
    assert result.processed[0].topic == "ai-security-research"
    assert result.processed[0].source == src

    # wiki/<topic>/README.md exists
    readme = vault_root / "wiki" / "ai-security-research" / "README.md"
    assert readme.exists()
    assert "# ai-security-research" in readme.read_text(encoding="utf-8")

    # wiki/<topic>/clippings/<safe>.md exists with body preserved
    page = (
        vault_root
        / "wiki"
        / "ai-security-research"
        / "clippings"
        / "2026-09-05_AI_Security_Research.md"
    )
    page_text = page.read_text(encoding="utf-8")
    assert "type: clipping" in page_text
    assert "topic: ai-security-research" in page_text
    assert "Body line 1." in page_text

    # Source moved to processed/
    assert not src.exists()
    assert (vault_root / "Clippings" / "processed" / "2026-09-05_AI_Security_Research.md").exists()


def test_process_clippings_appends_wiki_map_row(vault_root: Path, fixed_now) -> None:
    _write_clipping(
        vault_root,
        "ai_security_research.md",
        "# AI Security\n\n…\n",
    )
    process_clippings(vault_root, now=fixed_now, dry_run=False)
    map_md = (vault_root / "wiki-map.md").read_text(encoding="utf-8")
    assert "[[wiki/ai-security/README|ai-security]]" in map_md


def test_process_clippings_groups_multiple_clippings_same_topic(
    vault_root: Path, fixed_now
) -> None:
    _write_clipping(vault_root, "a.md", "# AI Security\n\nBody A.\n")
    _write_clipping(vault_root, "b.md", "# AI Security\n\nBody B.\n")
    result = process_clippings(vault_root, now=fixed_now, dry_run=False)

    assert len(result.processed) == 2
    # Both clippings live under the same topic dir.
    pages_dir = vault_root / "wiki" / "ai-security" / "clippings"
    assert (pages_dir / "a.md").exists()
    assert (pages_dir / "b.md").exists()
    # README created once.
    assert (vault_root / "wiki" / "ai-security" / "README.md").exists()


def test_process_clippings_splits_different_topics(vault_root: Path, fixed_now) -> None:
    _write_clipping(vault_root, "x.md", "# Topic A\n\n…\n")
    _write_clipping(vault_root, "y.md", "# Topic B\n\n…\n")
    process_clippings(vault_root, now=fixed_now, dry_run=False)
    assert (vault_root / "wiki" / "topic-a" / "README.md").exists()
    assert (vault_root / "wiki" / "topic-b" / "README.md").exists()


def test_process_clippings_excludes_processed_dir(vault_root: Path, fixed_now) -> None:
    # Pre-populate processed/ — must not be re-processed.
    proc = vault_root / "Clippings" / "processed"
    proc.mkdir(parents=True)
    (proc / "already.md").write_text("# Already Processed\n\nold.\n", encoding="utf-8")

    # Plus one fresh one to process.
    _write_clipping(vault_root, "fresh.md", "# Fresh\n\nnew.\n")

    result = process_clippings(vault_root, now=fixed_now, dry_run=False)
    processed_sources = {c.source.name for c in result.processed}
    assert "fresh.md" in processed_sources
    assert "already.md" not in processed_sources
    # already.md's body is unchanged (no new wiki entry for it).
    assert not (vault_root / "wiki" / "already-processed").exists()


def test_process_clippings_filename_collision_in_processed(
    vault_root: Path, fixed_now
) -> None:
    # Two files with the same basename ("a.md") under different timestamps.
    (vault_root / "Clippings" / "processed").mkdir(parents=True, exist_ok=True)
    (vault_root / "Clippings" / "processed" / "a.md").write_text("old", encoding="utf-8")
    _write_clipping(vault_root, "a.md", "# Topic\n\n…\n")
    result = process_clippings(vault_root, now=fixed_now, dry_run=False)

    # The new file did NOT clobber the existing processed/a.md.
    assert (vault_root / "Clippings" / "processed" / "a.md").read_text(encoding="utf-8") == "old"
    # And it landed at a unique path inside processed/.
    moved_to = Path(result.processed[0].moved_to)
    assert moved_to.parent == vault_root / "Clippings" / "processed"
    assert moved_to.name != "a.md"
    assert moved_to.exists()


def test_process_clippings_dry_run_makes_no_changes(
    vault_root: Path, fixed_now
) -> None:
    src = _write_clipping(vault_root, "x.md", "# Topic\n\n…\n")
    result = process_clippings(vault_root, now=fixed_now, dry_run=True)

    assert len(result.processed) == 1  # plan is reported
    assert src.exists()  # file NOT moved
    assert not (vault_root / "wiki").exists()  # no wiki created


def test_process_clippings_is_idempotent(vault_root: Path, fixed_now) -> None:
    _write_clipping(vault_root, "x.md", "# Topic\n\n…\n")
    r1 = process_clippings(vault_root, now=fixed_now, dry_run=False)
    assert len(r1.processed) == 1

    # Second run: nothing left in Clippings/ top level → processed==[].
    r2 = process_clippings(vault_root, now=fixed_now, dry_run=False)
    assert r2.processed == []


def test_process_clippings_creates_wiki_map_template_when_missing(
    vault_root: Path, fixed_now
) -> None:
    assert not (vault_root / "wiki-map.md").exists()
    _write_clipping(vault_root, "x.md", "# Topic\n\n…\n")
    process_clippings(vault_root, now=fixed_now, dry_run=False)
    text = (vault_root / "wiki-map.md").read_text(encoding="utf-8")
    assert "type: wiki-map" in text
    assert "## Topics" in text
    assert "obsidian-organize:wiki-map:auto-start" in text
    assert "obsidian-organize:wiki-map:auto-end" in text